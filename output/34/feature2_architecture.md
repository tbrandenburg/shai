# Feature 2 — A2A Integration Architecture

## 1. Architectural Intent
- **Objective** — Provide a deterministic adapter between `RouterCore` and the upstream `fasta2a_client.py` so that Telegram prompts reach the A2A network with full metadata, strict SLAs, and auditable results.
- **Operating model** — All work runs inside the uv event loop. Blocking sections of `fasta2a_client.py` execute in `asyncio.to_thread` so Router latency budgets (<12s P95) remain intact.
- **Design lens** — API-first contract separating orchestration (`A2AIntegrationService`) from transport (`Fasta2AClientAdapter`) so downstream developers, testers, and ops can replace or simulate each layer independently.

## 2. Service Boundaries & Responsibilities
| Boundary | Responsibilities | Inputs | Outputs |
| --- | --- | --- | --- |
| `RouterCore` | Authorize Telegram traffic, sanitize prompt text, determine persona tags/duty status, and call A2A integration with a `RouterCommand`. | `RouterCommand`, rate-limit + SLA context | `A2AResult` or raised `A2AIntegrationError` |
| `A2AIntegrationService` | Validate persona/configuration, enrich metadata envelope, enforce retries/timeouts, emit telemetry, and normalize upstream responses. | `RouterCommand`, config struct, observability handles | `A2AResult`, structured error events |
| `MetadataComposer` (subcomponent) | Generate `A2AEnvelopedRequest`, compute checksum, merge compliance + telemetry tags. | `RouterCommand`, persona registry | `A2AEnvelopedRequest` |
| `DispatchController` (subcomponent) | Invoke adapter, manage polling state machine, enforce SLA guard. | Enveloped request, timers | `A2ATaskOutcome`, retry signals |
| `Fasta2AClientAdapter` | Wrap `fasta2a_client.py`, inject auth headers, translate envelope to upstream `Message/TextPart`. | `A2AEnvelopedRequest`, env config | `A2ATaskHandle`, `A2ATaskState`, normalized artifacts |
| Upstream `A2AClient` | Execute `send_message` + `get_task` requests against remote agent. | HTTP requests | Task states, artifacts, server metadata |
| Telemetry Sink | Persist `a2a.request/response/failure` logs, counters, and histograms. | Structured log payloads | Metrics dashboards, alerts |

## 3. Interface Contracts

### 3.1 Router → Integration Boundary
```python
class A2AIntegrationService(Protocol):
    async def execute(self, command: RouterCommand) -> A2AResult: ...

@dataclass
class RouterCommand:
    correlation_id: str
    chat_id: str
    user: str
    persona_tag: Literal["Operator", "OnCall", "AutomationAuditor"]
    duty_status: Literal["primary", "secondary"]
    sanitized_text: str
    received_at: datetime
    telemetry: dict
    compliance_tags: dict
    redaction_rules: list[str]
```
`execute()` guarantees idempotency through `correlation_id` and returns a normalized `A2AResult` (see §3.4). Errors raise `A2AIntegrationError` with `classification`, `attempt_count`, and `metadata` fields.

### 3.2 Metadata Envelope
```yaml
A2AEnvelopedRequest:
  correlation_id: string (ULID)
  message_id: uuid4
  chat_id: string
  user: string
  persona_tag: enum (Operator, OnCall, AutomationAuditor)
  duty_status: enum (primary, secondary)
  received_at: datetime
  prompt_checksum: sha256 string
  telemetry:
    source: "telegram_router"
    version: semver
    environment: string
  compliance_tags: object
  persona_context: object
  redaction_rules: [string]
  trace:
    queue_depth: int
    semaphore_slots: int
  sanitized_text: string
```
The `MetadataComposer` maps this envelope to the upstream schema, duplicating correlation/message IDs inside both `Message.metadata` and each `TextPart.metadata` block for traceability.

### 3.3 Adapter Contract
```python
class Fasta2AClientAdapter(Protocol):
    async def run(self, request: A2AEnvelopedRequest) -> A2ATaskOutcome: ...

@dataclass
class A2ATaskOutcome:
    task_id: str
    final_state: Literal["completed", "failed", "canceled", "rejected", "timeout"]
    attempt_count: int
    latency_ms: int
    artifacts: list[str]
    server_messages: list[str]
```
The adapter injects `Authorization: Bearer <A2A_API_KEY>` when configured, enforces HTTPS-only `A2A_BASE_URL` outside dev sandboxes, and encapsulates polling inside its own executor thread. Any exception is wrapped in `A2AAdapterError` carrying `recoverable: bool` to guide retry decisions by the service.

### 3.4 Normalized Response
```yaml
A2AResult:
  status: enum[success, transient_error, fatal_error]
  body: string (UTF-8)
  metadata:
    correlation_id: string
    task_id: string
    final_state: string
    attempt_count: int
    upstream_latency_ms: int
    persona_tag: string
    server_messages: [string]
```
Binary or multi-artifact responses are collapsed into text with warnings referencing the quarantine location to preserve confidentiality promises.

## 4. Timeout, Polling, and Retry Controls
| Control | Default | Owner | Behavior |
| --- | --- | --- | --- |
| `A2A_POLL_INTERVAL_SECONDS` | 2s ±200ms jitter | DispatchController | Sleep between `get_task` calls; jitter prevents lockstep bursts. |
| `A2A_POLL_TIMEOUT_SECONDS` | 30s | DispatchController | Hard ceiling per attempt; raises `transient_error` when exceeded. |
| `A2A_MAX_POLLS` | Derived (`timeout ÷ interval`) | DispatchController | Guardrail preventing runaway loops even if timeout misconfigured. |
| `A2A_RETRY_LIMIT` | 1 | RetryOrchestrator | Applies to transient failures (timeouts, HTTP 5xx, `canceled`, JSON decode). |
| `A2A_RETRY_BACKOFF_SECONDS` | 2s base, ×2 multiplier, max 8s | RetryOrchestrator | Aligns with Router-level backoff to keep <12s P95 SLA. |
| Telegram SLA Guard | 12s P95 across intake→reply | RouterCore | Cancels in-flight A2A call if cumulative latency threatens SLA; returns holding message w/ task ID. |
| `A2A_API_KEY_ISSUED_AT` | ISO timestamp | ConfigRegistry | Startup validation fails if key age >90d to honor rotation policy. |

Timers live inside the integration service so downstream code need only await `execute()`. The SLA guard uses monotonic timers to abort polling early and instruct the adapter to cancel outstanding tasks when possible.

## 5. Error Propagation & Signaling
| Source Event | Detection Point | Classification | Router Action | Telemetry |
| --- | --- | --- | --- | --- |
| `httpx.ConnectError`, TLS failures | Adapter send/poll | `transient_error` | Retry within limit; final response instructs operator to re-issue. | `a2a.failure` (`reason=transport`) + counter increment |
| HTTP 5xx / JSON decode issues | Adapter poll loop | `transient_error` | Retry once; include upstream status in body metadata. | Emit latency + error counters |
| HTTP 4xx (≠429) or upstream `failed/rejected` | Adapter final state | `fatal_error` | No retry; respond with upstream message + persona guidance. | `a2a.failure` (`reason=caller`) |
| 429 with optional `Retry-After` | Adapter poll | `transient_error` | Sleep indicated value (bounded by SLA) before final retry. | `a2a.retry_total` + histogram bucket |
| `canceled` state mid-poll | Adapter | `transient_error` | Retry if SLA headroom remains, else respond with cancellation note. | Cancellation metric |
| SLA timeout (Router guard) | DispatchController | `transient_error` | Send holding reply, continue background poll up to 12s total, then emit `timeout`. | `a2a.timeout_total` |
| Unexpected artifact type | Normalizer | `fatal_error` (masked payload) | Return warning referencing quarantine pointer. | `a2a.failure` (`reason=artifact`) |

All failures raise `A2AIntegrationError` with fields `{classification, task_id?, correlation_id, attempt_count, upstream_state}` so Router logging and tests can assert behavior deterministically.

## 6. Sequence Views

### 6.1 Successful Invocation
```mermaid
sequenceDiagram
    participant TG as RouterCore
    participant INT as A2AIntegrationService
    participant AD as Fasta2AClientAdapter
    participant A2A as Upstream A2AClient

    TG->>INT: RouterCommand (sanitized, persona, metadata)
    INT->>INT: Validate persona + config
    INT->>INT: Compose A2AEnvelopedRequest
    INT->>AD: run(enveloped_request)
    AD->>A2A: POST /send_message
    A2A-->>AD: task_id
    loop Poll until final state
        AD->>A2A: GET /tasks/{task_id}
        A2A-->>AD: state snapshot
        AD-->>INT: state, latency
        INT->>INT: SLA guard + retry budget check
    end
    AD-->>INT: A2ATaskOutcome(final_state=completed)
    INT->>INT: Normalize artifacts → A2AResult(success)
    INT-->>TG: A2AResult + metadata
    INT->>Telemetry: a2a.request/response metrics
```

### 6.2 Failure w/ Retry then Timeout
```mermaid
sequenceDiagram
    participant TG as RouterCore
    participant INT as A2AIntegrationService
    participant AD as Fasta2AClientAdapter
    participant A2A as Upstream A2AClient

    TG->>INT: RouterCommand
    INT->>AD: run(request)
    AD->>A2A: POST /send_message
    A2A-->>AD: task_id
    loop Poll attempt #1
        AD->>A2A: GET /tasks/{task_id}
        A2A-->>AD: final_state = failed (HTTP 5xx)
        AD-->>INT: transient_error + attempt_count=1
    end
    INT->>INT: Retry budget remaining? yes
    Note over INT: Backoff wait = 2s (bounded by SLA)
    INT->>AD: run(request) attempt #2
    AD->>A2A: POST /send_message
    A2A-->>AD: task_id
    loop Poll attempt #2
        AD->>A2A: GET /tasks/{task_id}
        A2A-->>AD: still running
        INT->>INT: SLA guard exceeds 12s
    end
    INT-->>AD: cancel(task_id)
    AD-->>INT: timeout state
    INT-->>TG: A2AResult(status=transient_error, body="Timed out after 10s", metadata task_id)
    INT->>Telemetry: a2a.timeout_total++, emit holding message event
```

## 7. Security, Configuration, and Observability Anchors
- **Configuration validation** — Startup uses `ConfigRegistry` to ensure `A2A_BASE_URL` is HTTPS (unless `ENV=dev`), optional `A2A_API_KEY` age <90d, and persona allowlist matches `A2A_ALLOWED_PROMPT_TAGS`. Fail fast with structured `config.error` log when requirements are unmet.
- **Auth & transport hardening** — The adapter loads secrets from memory only, registers the upstream `AuthInterceptor`, and enforces TLS 1.2+. Non-TLS origins trigger `reduced_trust` mode logs unless explicitly allowed via `A2A_ALLOW_INSECURE=true` in local dev.
- **Metadata hygiene** — Cleartext usernames are passed upstream but hashed in logs. Prompt text is never persisted; only the SHA256 checksum plus metadata envelopes reach storage.
- **Observability** — Emit counters (`a2a_success_total`, `a2a_transient_error_total`, `a2a_fatal_error_total`, `a2a_retry_total`) and histograms (`a2a_latency_ms`). Telegram `/status` command surfaces latest latency percentiles plus persona-sliced metrics.
- **Extensibility** — Componentized boundaries make it straightforward to plug alternate clients (REST, gRPC) or additional persona tags without touching Router transport logic. The architecture also enables integration tests to mock `Fasta2AClientAdapter` and assert retry/error branches.

This architecture document is the authoritative input for the downstream design and implementation stages of Feature 2.
