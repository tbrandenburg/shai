# A2A Integration Design

## 1. Scope & Objectives
- Translate the requirements in `output/34/feature2_requirements.md` and system boundaries in `output/34/feature2_architecture.md` into actionable implementation guidance for the Feature 2 adapter.
- Provide deterministic module contracts (`services/a2a_integration.py`, `services/a2a_adapter.py`, and supporting helpers) so the Telegram router can forward prompts to the upstream `fasta2a_client.py` without ambiguity.
- Explicitly cover client abstractions, telemetry hooks, response normalization, configuration injection, and persona-aligned retry controls so backend, QA, and Ops teams can reason about the code path without rediscovering expectations.

## 2. Runtime Overview
1. `bots/telegram_router.py` acquires an adapter instance via `services.a2a_adapter.build_adapter()`; the adapter exposes the `RouterAdapter` protocol that currently powers the echo fallback.
2. The adapter wraps an `A2AIntegrationService` hosted in `services/a2a_integration.py`. The service orchestrates metadata enrichment, persona validation, SLA guards, retry state, and telemetry emission before delegating to a transport-specific adapter.
3. `Fasta2AClientAdapter` (also under `services/`) owns all interactions with `fasta2a_client.py`. Blocking upstream calls execute inside `asyncio.to_thread` to keep the uv loop responsive, and results are mapped back into normalized structures the router already expects.
4. Configuration flows through a validated `A2AConfig` dataclass sourced from environment variables and injected at adapter construction time. Telemetry/log exporters are injected alongside config to keep outputs deterministic during testing.

## 3. Module Responsibilities
### 3.1 `services/a2a_config.py`
- Defines `A2AConfig` plus `load_a2a_config()` helper that validates env vars (`A2A_BASE_URL`, `A2A_API_KEY`, `A2A_POLL_INTERVAL_SECONDS`, `A2A_POLL_TIMEOUT_SECONDS`, `A2A_RETRY_LIMIT`, `A2A_RETRY_BACKOFF_SECONDS`, `A2A_ALLOWED_PROMPT_TAGS`, `A2A_API_KEY_ISSUED_AT`, `A2A_ALLOW_INSECURE`).
- Computes derived values (`max_polls = timeout // interval`, jitter bounds) and enforces TLS-by-default requirements (non-HTTPS origins rejected when `allow_insecure` is false).
- Ensures persona allowlists match Feature 2 canonical tags; misconfigurations raise `ConfigError` before router startup completes.

### 3.2 `services/a2a_metadata.py`
- Implements `MetadataComposer` that accepts a `RouterCommand` (from Feature 1) and returns an `A2AEnvelopedRequest` containing the metadata table from the requirements.
- Generates UUID4 `message_id`, calculates SHA256 checksum of sanitized prompt, and mirrors persona/compliance fields into both message-level and part-level metadata payloads.
- Encapsulates persona-specific additions (IncidentCommander incident IDs, AutomationAuditor compliance scope) and ensures redaction lists accompany every part.

### 3.3 `services/a2a_integration.py`
- Exposes `class A2AIntegrationService(RouterAdapter)` implementing `async invoke(request: A2ARequest) -> A2AResponse` so `bots/telegram_router.py` can drop in the new adapter without refactoring.
- Performs persona/config validation, composes envelopes, enforces SLA guard timers, manages retry attempts, and normalizes upstream outcomes into `A2AResponse` objects.
- Emits telemetry hooks (`a2a.request`, `a2a.response`, `a2a.failure`, `a2a.retry`) through injected logger/metrics interfaces.

### 3.4 `services/a2a_adapter.py`
- Contains `Fasta2AClientAdapter` responsible for translating `A2AEnvelopedRequest` into the upstream `Message/TextPart` schema provided by `fasta2a_client.py`.
- Configures the upstream client with HTTPX timeout settings, TLS requirements, and optional `AuthInterceptor` when `A2A_API_KEY` is set.
- Normalizes `send_message` and `get_task` responses into `A2ATaskOutcome` records consumed by the integration service.
- Offers `build_adapter(*, config: A2AConfig | None = None, telemetry: TelemetryHandles | None = None)` factory that the router calls. Defaults to loading config on demand when not injected explicitly (tests pass stubs).

### 3.5 `services/a2a_errors.py`
- Defines exception hierarchy used across modules:
  - `A2AIntegrationError` with fields `classification`, `task_id`, `attempt_count`, `metadata`.
  - `A2AAdapterError` with flag `recoverable` for transient vs fatal upstream signals.
  - `ConfigError` reuse for startup validation issues.
- Exception payloads are structured dicts so logging/metrics can reference failure modes consistently.

### 3.6 `services/a2a_telemetry.py`
- Groups logging/metrics helpers used by both the integration service and adapter.
- Provides `TelemetryHandles` dataclass bundling `logger`, `metrics`, and `tracer` interfaces with defaults pointing to `logging.getLogger("a2a")` and no-op metrics if not supplied.
- Exposes helper functions `emit_request`, `emit_response`, `emit_failure`, `emit_retry`, `emit_timeout`, and `record_latency_histogram` to keep labels consistent with Feature 1 expectations.

## 4. Data Contracts
### 4.1 Router Command Intake
`bots/telegram_router.py` already uses the lightweight `A2ARequest` dataclass. During Feature 2 implementation, extend/replace it with the enriched `RouterCommand` variant defined in `output/34/feature2_architecture.md`.

### 4.2 Configuration
```python
@dataclass(slots=True)
class A2AConfig:
    base_url: AnyHttpUrl
    api_key: str | None
    poll_interval_s: float = 2.0
    poll_timeout_s: float = 30.0
    retry_limit: int = 1
    retry_backoff_s: float = 2.0
    retry_backoff_multiplier: float = 2.0
    retry_backoff_max_s: float = 8.0
    allowed_persona_tags: frozenset[str] = frozenset({"Operator","OnCall","IncidentCommander","AutomationAuditor"})
    api_key_issued_at: datetime | None = None
    allow_insecure: bool = False
    environment: str = "dev"
```
Derived helpers:
- `config.max_polls = math.floor(config.poll_timeout_s / config.poll_interval_s)`
- `config.jitter_bounds = (-0.2 * interval, +0.2 * interval)` for randomized sleeps
- `config.sla_budget_s = 12.0` (mirrors router guard) with possible persona overrides

### 4.3 Envelope Structures
```python
@dataclass(slots=True)
class A2AEnvelopedRequest:
    correlation_id: str
    message_id: str
    chat_id: str
    user: str
    persona_tag: str
    duty_status: str
    received_at: datetime
    prompt_checksum: str
    telemetry: dict[str, Any]
    compliance_tags: dict[str, Any]
    persona_context: dict[str, Any]
    trace: dict[str, Any]
    redaction_rules: list[str]
    sanitized_text: str
    envelope_version: int = 1
```
- `MetadataComposer` mirrors `correlation_id`, `message_id`, `persona_tag`, and `prompt_checksum` into `message_metadata` and each `TextPart` metadata dict.

### 4.4 Adapter Request & Outcome
```python
@dataclass(slots=True)
class A2AAdapterRequest:
    envelope: A2AEnvelopedRequest
    config: A2AConfig

@dataclass(slots=True)
class A2ATaskOutcome:
    task_id: str
    final_state: Literal["completed","failed","canceled","rejected","timeout"]
    attempt_count: int
    latency_ms: int
    server_messages: list[str]
    artifacts: list[str]
    upstream_state: dict[str, Any]
```

### 4.5 Normalized Result
```python
@dataclass(slots=True)
class A2AResponse:
    final_state: Literal["success","transient_error","fatal_error"]
    text: str
    task_id: str
    metadata: dict[str, Any]
    retryable: bool
    latency_ms: int
```
- `metadata` must include `{ "correlation_id", "persona_tag", "attempt_count", "final_state", "upstream_state" }` and is what the router forwards to Telegram + telemetry sinks.

## 5. Control Flows
### 5.1 Execution Path
1. Router enqueues an `A2ARequest`; `resolve_adapter()` instantiates `A2AIntegrationService` if not provided.
2. `A2AIntegrationService.invoke()` converts `A2ARequest` → `RouterCommand` (adding persona metadata from router context) and ensures persona tags belong to `config.allowed_persona_tags`.
3. Compose envelope via `MetadataComposer.compose(command)`.
4. Call `_dispatch(envelope)` which tracks attempt counters, SLA deadlines, and persona-specific retry allowances.
5. `_dispatch` delegates to `Fasta2AClientAdapter.run(A2AAdapterRequest)` for each attempt. The adapter returns `A2ATaskOutcome` once `get_task` reaches a terminal state or times out.
6. Normalize `A2ATaskOutcome` into `A2AResponse` + telemetry events; insert retry cache record for `/retry` flows.

### 5.2 Polling + Retry State Machine
Pseudo-code:
```python
async def _dispatch(self, envelope: A2AEnvelopedRequest) -> A2AResponse:
    deadline = monotonic() + self._sla_budget(persona=envelope.persona_tag)
    attempt = 1
    while True:
        outcome = await self._run_single_attempt(envelope, attempt, deadline)
        if outcome.final_state in {"failed","rejected"}:
            return self._normalize(outcome, retryable=False)
        if outcome.final_state == "completed":
            return self._normalize(outcome, retryable=False)
        if not self._can_retry(persona=envelope.persona_tag, attempt=attempt, outcome=outcome):
            return self._normalize(outcome, retryable=False)
        attempt += 1
        await asyncio.sleep(self._compute_backoff(attempt, persona=envelope.persona_tag))
```
Key behaviors:
- SLA guard cancels outstanding tasks when `monotonic() >= deadline`, surfaces `transient_error`, and instructs router to send holding reply.
- `A2A_RETRY_LIMIT` applies globally; persona matrix further constrains automatic retries.
- Timeout states from adapter (`timeout` or `canceled`) count toward retry budget but emit telemetry reason `timeout`.

### 5.3 Response Normalization
- Map upstream states: `completed → success`, `failed/rejected → fatal_error`, `canceled/timeout/http errors → transient_error`.
- `text` resolution order: first non-empty artifact string → fallback to joined `server_messages` → deterministic error template referencing `task_id` + `correlation_id`.
- Attach `metadata` with `persona_tag`, `compliance_tags`, `trace`, `attempt_count`, `latency_ms`, `upstream_state`, `prompt_checksum`, and `A2A_BASE_URL` fingerprint (hash only).

### 5.4 Persona Retry Matrix
| Persona | Auto Attempts | Timeout Override | Notes |
| --- | --- | --- | --- |
| Operator | 1 automatic retry (transient only) | `deadline = now + 12s` | Manual `/retry` unlimited if queue depth ≤3. |
| OnCall | 1 automatic retry if queue depth <2 | `deadline = now + 12s` | Manual retries capped at one extra attempt. |
| IncidentCommander | 0 auto retries | `deadline = now + 8s` | Preemption flag instructs adapter to send `queue_priority=0`. |
| AutomationAuditor | 0 auto retries | `deadline = now + 10s` | Abort polling early (>4s) to protect compliance budgets. |

## 6. Configuration & Dependency Injection
- `services/a2a_adapter.build_adapter()` accepts optional overrides:
  ```python
  def build_adapter(*, config: A2AConfig | None = None, telemetry: TelemetryHandles | None = None) -> RouterAdapter:
      config = config or load_a2a_config()
      telemetry = telemetry or TelemetryHandles.default()
      return A2AIntegrationService(config=config, telemetry=telemetry, transport=Fasta2AClientAdapter(config, telemetry))
  ```
- Router startup supplies `AdapterDependencies` dataclass (config, telemetry, persona registry, queue monitor) when available; tests construct fake transport objects to verify retries and normalization without hitting network.
- `.env.example` gains A2A variables grouped under an "A2A" heading. `RouterConfig.load()` remains responsible for verifying TELEGRAM values; `load_a2a_config()` is invoked during adapter initialization.
- Config validation rejects plaintext HTTP origins outside `A2A_ALLOW_INSECURE=true` dev mode and warns when `api_key_issued_at` is ≥75 days (error at ≥90 days). The adapter surfaces fingerprint + key age via `/status` telemetry so Ops can detect drift.

## 7. Telemetry & Observability
- Structured logs (JSON) produced at each stage:
  - `a2a.request` — fields `{correlation_id, persona_tag, attempt, task_id?, base_url_hash}`
  - `a2a.response` — `{final_state, latency_ms, attempt_count, persona_tag, queue_depth}`
  - `a2a.failure` — `{reason, http_status?, exception, retryable}`
- Metrics:
  - Counters: `a2a_success_total`, `a2a_transient_error_total`, `a2a_fatal_error_total`, `a2a_retry_total`, `a2a_timeout_total`.
  - Histograms: `a2a_latency_ms`, `a2a_poll_round_ms` (per `get_task` loop), `a2a_send_message_ms`.
  - Gauges: `a2a_secret_age_days`, `a2a_queue_depth_proxy` (mirrors router queue depth to correlate with upstream lag).
- Tracing: create OTEL spans `A2AIntegration.execute`, `A2AIntegration.poll`, `Fasta2AClient.run`. Attach attributes for `task_id`, `persona_tag`, `attempt`, `final_state`.
- Telemetry handles plug into the router's existing metrics exporter so `/status` can echo aggregated latency buckets plus latest API key fingerprint (SHA-256 prefix only).

## 8. Error Handling & Logging
- Adapter catches `httpx.ConnectError`, TLS errors, JSON decode issues, and wraps them in `A2AAdapterError(recoverable=True)` to trigger retries. HTTP 4xx other than 429 result in `recoverable=False` and map to `fatal_error`.
- Integration service wraps adapter errors into `A2AIntegrationError` with `classification` ∈ {`transient_error`, `fatal_error`, `config_error`}.
- SLA timeout detection raises `A2AIntegrationError(classification="transient_error", metadata={"reason":"sla_guard", "deadline":deadline})` and logs `a2a.timeout_total` before returning a holding reply to the router.
- Persona validation errors short-circuit before hitting the adapter, log `reason="persona_unmapped"`, and return deterministic fatal responses instructing operators to contact admins.
- Secrets, raw prompts, and usernames never appear in logs; hashed surrogates (SHA-256 + salt) align with Feature 1 confidentiality rules.

## 9. Testing Strategy
1. **Unit tests (`tests/test_a2a_integration.py`)** covering:
   - Persona validation + allowlist enforcement
   - MetadataComposer output parity with requirements table
   - Retry matrix enforcement (Operator vs AutomationAuditor)
   - SLA guard timing (mock `time.monotonic`)
2. **Adapter tests (`tests/test_a2a_adapter.py`)** with mocked `fasta2a_client` to assert:
   - HTTPS enforcement and `allow_insecure` override
   - Authorization header injection when API key present
   - Timeout + polling loops convert states correctly
   - Unexpected artifacts route to quarantine warning text
3. **Integration tests** wiring router + adapter with stubbed `fasta2a_client` verifying queue/resend flows, ensuring telemetry counters increment as expected.
4. **Contract tests** referencing recorded HTTP interactions from upstream repo to guarantee payload schemas match `Message` / `TextPart` expectations.
5. **Smoke tests** executed in CI calling `build_adapter()` with `.env.example` values to ensure config validation prevents unsafe deployments.

## 10. Implementation Checklist
1. Create `services/a2a_config.py` with validated env loader + derived fields.
2. Implement `services/a2a_metadata.py` and unit tests for metadata envelopes.
3. Build `services/a2a_telemetry.py` no-op capable handles plus log helpers.
4. Implement `services/a2a_errors.py` with integration + adapter exception classes.
5. Implement `services/a2a_adapter.py` wrapping `fasta2a_client.py`, including HTTPX timeout configuration, TLS enforcement, auth interceptor wiring, and artifact normalization helpers.
6. Implement `services/a2a_integration.py` orchestrating metadata compose, SLA guard, retry matrix, and response normalization. Ensure it satisfies `RouterAdapter` protocol expected by `bots/telegram_router.py`.
7. Update `bots/telegram_router.resolve_adapter()` to call `services.a2a_adapter.build_adapter()` (already scaffolded) and pass router telemetry handles.
8. Refresh `.env.example` with A2A variables referenced by `A2AConfig`.
9. Author unit/integration tests plus `tests/test_a2a_adapter.py` per Feature 2 testing requirements.
10. Document usage + config in `docs/telegram_usage.md` (already partially handled) and ensure `/status` surfaces adapter health/metrics.

This design provides the exhaustive guidance needed to rebuild the Feature 2 A2A integration so implementation, testing, and deployment remain aligned with the approved requirements and architecture artifacts.
