# Feature 2 — A2A Integration Requirements

## Source Inputs
- Issue #34 context and conversation (`output/34/issue_conversation.md`) requesting a uv-based Telegram bot that proxies prompts to the upstream `fasta2a_client.py` agent and returns results to the authorized chat.
- Feature 1 deliverables: routing requirements (`output/34/feature1_requirements.md`), architecture notes (`output/34/feature1_architecture.md`), backend design (`docs/telegram_routing_design.md`), and implemented bot (`bots/telegram_router.py`).
- Upstream reference implementation (`pydanticai-a2a` repo) where `fasta2a_client.py` constructs an `A2AClient`, issues `send_message` calls, and polls task status via HTTPX (`run_client.py`).
- Current upstream script snapshot (`https://raw.githubusercontent.com/tbrandenburg/pydanticai-a2a/main/fasta2a_client.py`, fetched 2025-11-18) confirming final state names (`completed`, `failed`, `canceled`, `rejected`) and the exact Message/TextPart schema leveraged by `A2AClient`.

## Business Objective
Enable the Telegram router to invoke the external A2A agent/network through the upstream `fasta2a_client.py` wrapper with auditable metadata, deterministic retries, and confidentiality controls so that operators can rely on consistent, low-latency responses without exposing secrets or unsanitized prompts.

## Scope & Assumptions
- Scope covers the adapter between `RouterCore` and the upstream `fasta2a_client.py` script plus the requirements for prompt metadata, retries, and confidentiality. Telegram transport and dispatcher requirements remain governed by Feature 1.
- `fasta2a_client.py` exposes a synchronous `run(payload: dict)` entrypoint that internally uses the async `A2AClient`. Our `Fasta2AClient` wrapper (see `bots/telegram_router.py`) will continue to run this code inside `asyncio.to_thread/run_in_executor` to avoid blocking uvloop.
- A2A service is reachable over HTTPS, requires a base URL, and may require API tokens; these values will be injected through environment variables (see configuration table below).

## A2A Invocation Flow Requirements
1. **Command Intake** — `RouterCore` already assembles a `RouterCommand` with `sanitized_text`, `chat_id`, `user`, and `correlation_id`. Before invoking A2A, enrich this command with persona tags (Operator vs On-Call), message timestamps, and trace-friendly metadata.
2. **Payload Construction** — `Fasta2AClient.run()` must map the `RouterCommand` into the upstream schema expected by `A2AClient`:
   - Instantiate `Message(role="user", kind="message", message_id=<uuid>, parts=[TextPart(text=<sanitized_text>, kind="text", metadata=<per-part metadata>)], metadata=<envelope metadata>)`.
   - Call `await client.send_message(message)` and capture the returned task identifier.
3. **Polling Loop** — Poll `client.get_task(task_id)` every `A2A_POLL_INTERVAL_SECONDS` (default 2s) until status ∈ {`completed`, `failed`, `canceled`, `rejected`} or timeout `A2A_POLL_TIMEOUT_SECONDS` (default 30s) is exceeded.
4. **Result Normalization** — When the task reaches a final state, normalize into `A2AResult`:
   - `status` mapping: `completed` → `success`; `failed`/`rejected` → `fatal_error`; `canceled` or transport exceptions without completion → `transient_error`.
   - `body` = first artifact text when available; fallback to structured error text with remediation guidance.
   - Artifact media expectation: the upstream restaurant agent (`server_simple.py`/`server_mcp.py`) and `fasta2a_client.py` only exchange `TextPart` artifacts today, so treat all responses as UTF-8 text. If an unexpected non-text part arrives, preserve the binary payload in storage, reply with a short warning plus metadata pointer, and skip inline rendering.
   - `metadata` must include `task_id`, `final_state`, `attempt_count`, upstream latency, and any server messages.
5. **Error Surfacing** — HTTP failures (`httpx.ConnectError`, `UnexpectedResponseError`) and schema surprises must raise descriptive exceptions so `RouterCore` metrics/logs remain accurate.

## Required Prompt Metadata Envelope
| Field | Source | Requirement |
| --- | --- | --- |
| `correlation_id` | `RouterCommand` (ULID `tg-<update_id>`) | Propagate untouched; include inside `Message.metadata` and `TextPart.metadata` to maintain traceability end-to-end. |
| `message_id` | Generated UUID per invocation | Required by `A2AClient`; store in metadata + logs for replay.
| `chat_id` | `RouterCommand.chat_id` | Pass in payload to allow upstream auditing; never expose outside authorized chat. |
| `user` | `RouterCommand.user` | Include sanitized Telegram username for accountability. |
| `persona_tag` | Derived from operator role (Operator / On-Call / Auditor) | Insert in metadata; allows upstream prompt orchestration to adjust behavior. |
| `received_at` | `RouterCommand.received_at` timestamp (ISO-8601) | Enables SLA tracking and drift analysis. |
| `prompt_checksum` | SHA256 of sanitized text | Stored in metadata only; prevents raw prompt replay while enabling dedupe checks. |
| `telemetry` | `{"source":"telegram_router","version":"1.x","environment":"<env>"}` | Enables the upstream agent to route analytics back to the originating service version. |
| `compliance_tags` | Derived from deployment environment (e.g., `{"region":"us-east-1","classification":"confidential"}`) | Informs upstream guardrails about data classification requirements. |
| `persona_context` | `{"persona":"A2A Operator","duty_status":"primary"}` | Allows the agent to tailor response tone and escalation paths. |
| `redaction_rules` | List of patterns already stripped during sanitization | Documents what was removed locally so the upstream agent does not attempt redundant scrubbing. |
| `trace` | `{"queue_depth":<int>,"semaphore_slots":<int>}` | Optional; improves debugging when upstream performance issues arise. |
 
### Canonical Persona Tags
- `Operator` — Actively maintains upstream workflows; matches the A2A Operator persona defined in `output/34/feature1_requirements.md`.
- `OnCall` — Shares operational authority while covering after-hours escalations; use the `OnCall` tag to satisfy telemetry constraints that distinguish duty status.
- `IncidentCommander` — Sev-1 lead who can pre-empt queues, inspect `/throttle` state, and demand extra metadata for audit playback.
- `AutomationAuditor` — Read-only oversight role; prompts flagged with this tag should never request mutative operations and may be throttled upstream.
 
Treat these four tags as the canonical `A2A_ALLOWED_PROMPT_TAGS` default. Reject or translate any other persona labels before dispatch so upstream guardrails stay deterministic.
 
#### Persona Metadata Matrix
| Persona Tag | Metadata Additions | Auto Retry Budget | Notes |
| --- | --- | --- | --- |
| Operator | `persona_context` includes `{ "duty_status":"primary", "queue_priority":2, "command_scope":"operations" }` plus hashed Telegram user ID + ULID correlation. | 1 automatic retry for transient errors, unlimited manual `/retry`. | Baseline persona used for most prompts; inherits Feature 1 SLA targets. |
| OnCall | Add `{ "duty_status":"secondary", "queue_priority":3, "handoff":"<timestamp>" }` plus the on-call schedule identifier. | 1 automatic retry, capped at 2 total attempts including manual request. | Ensures after-hours responders cannot overwhelm the adapter. |
| IncidentCommander | Must attach `{ "incident_id":"sev1-<id>", "command_authority":"sev1", "queue_priority":0 }` and echo the current incident bridge URL. | 0 automatic retries; manual `/retry` allowed but requires explicit operator confirmation metric. | Preempts queue (ahead of Operator) yet remains auditable via hashed `incident_commander_id`. |
| AutomationAuditor | Append `{ "audit_scope":"read-only", "queue_priority":4, "sensitivity":"confidential" }` along with compliance case ID. | 0 automatic retries; manual replay forbidden. | Read-only flows, primarily for transcript exports. |
 
### Persona Tagging & Routing Rules
- The router determines persona tags using the Feature 1 persona table (Operators, On-Call, Incident Commander, Automation Auditor) and persists the tag beside the Telegram user ID hash before invoking A2A. Missing or conflicting inputs cause the adapter to block dispatch and return a "persona_unmapped" error.
- Each outgoing request includes both the canonical tag and a duty status (e.g., `{ "persona":"Operator", "duty_status":"primary" }`). Duty status is derived from the same on-call schedule file already referenced by Feature 1 acceptance metrics.
- Persona tags decide retry policy: Operator prompts can trigger automatic retries, On-Call prompts trigger a single retry, IncidentCommander prompts never retry automatically (manual only to avoid oscillations), and AutomationAuditor prompts never retry automatically (to avoid repeated compliance queries).
- IncidentCommander prompts must inject `incident_id`, `bridge_url`, and queue-preemption metadata so `Fasta2AAdapter` can move them ahead of the single-flight queue while still logging the override with hashed commander ID.
- Responses echo persona tags back to Telegram with the A2A task ID so that downstream transcripts remain aligned with audit personas.


### Metadata Envelope Structure
- **Message-level metadata (`Message.metadata`)** — Must include `correlation_id`, `chat_id`, `user`, `received_at`, `telemetry`, `compliance_tags`, `persona_context`, and `trace` structures outlined in the table above. Append `envelope_version` (start at `1`) so downstream services can evolve schema safely.
- **Part-level metadata (`TextPart.metadata`)** — Embed `persona_tag`, `prompt_checksum`, `redaction_rules`, and per-part language/format hints (e.g., `{ "content_type":"text/plain","language":"en" }`). The adapter enforces parity between part metadata and message metadata for `correlation_id` and `message_id` to keep audit trails intact.
- **Server echo metadata** — On receipt, normalize upstream `status.message`, `attempt_count`, and latency ms into the response metadata block that `RouterCore` sends back to Telegram. Store the latest metadata in the in-memory conversation window for Operator replay commands.

## Adapter Configuration Inputs

| Variable | Requirement | Notes |
| --- | --- | --- |
| `A2A_BASE_URL` | Required. URI for the upstream agent service; must default to `https://` and support override per environment. | Mirror value passed into `A2AClient(base_url=...)`. |
| `A2A_API_KEY` | Optional/required depending on upstream deployment. Load from secrets manager and inject as HTTP header within `fasta2a_client.py`. | Never log or echo in Telegram replies. |
| `A2A_POLL_INTERVAL_SECONDS` | Default 2s; tunable for slower/faster upstreams. | Value drives the polling loop sleep duration. |
| `A2A_POLL_TIMEOUT_SECONDS` | Default 30s; maximum wait before declaring timeout. | Timeout surfaced as `transient_error` with actionable text. |
| `A2A_MAX_POLLS` | Derived from timeout ÷ interval to cap requests. | Prevents infinite loops and reduces load. |
| `A2A_RETRY_LIMIT` | Default 1 retry for transient failures as defined below. | Keeps behavior aligned with Feature 1 architecture notes. |
| `A2A_RETRY_BACKOFF_SECONDS` | Default 2s base, multiplier 2x, max 8s. | Aligns with router retry settings for consistent observability. |
| `A2A_ALLOWED_PROMPT_TAGS` | Enumerated string list (e.g., `{"Operator","OnCall"}`). | Used to validate persona metadata before dispatch. |
 
### Authentication Binding Map
| Binding Layer | Requirement | Traceability |
| --- | --- | --- |
| Env loader → Adapter config | `RouterCore` hydrates a dedicated `A2AConfig` structure that validates `A2A_BASE_URL` is TLS, derives `A2A_MAX_POLLS = timeout ÷ interval`, and loads secrets only into memory. Missing or plaintext values force startup failure outside `DEV_MODE`. | `bots/telegram_router.py` settings bootstrap + `.env.example` entries. |
| Adapter → `fasta2a_client.A2AClient` | `Fasta2AAdapter` passes the validated base URL, injects the `AuthInterceptor` when `A2A_API_KEY` is present, and threads poll/backoff parameters into every `send_message`/`get_task` call so the upstream client mirrors our SLA math. | `services/a2a_adapter.py` (new implementation) calling upstream `fasta2a_client.py`. |
| HTTP transport → Observability | When constructing `A2AClient`, configure HTTPX timeouts (connect/read ≤1s each), TLS 1.2+, and attach request IDs so telemetry can tie adapter retries to upstream responses. Capture elapsed timings per call for the latency histograms below. | `fasta2a_client.py` instrumentation hooks + `a2a.request/response` logs. |
| Secrets rotation → Health telemetry | Hash (`sha256`) the current `A2A_API_KEY` and surface the age + hash prefix in `/status`, matching the TELEGRAM token governance from Feature 1. Refuse promotion when key age ≥90 days or when fingerprints diverge from secrets manager records. | `/status` command output + deployment health automation. |
 
## Authentication & Access Control Rules
1. **Transport defaults** — The upstream reference agent defined in `server_simple.py`/`server_mcp.py` (tbrandenburg/pydanticai-a2a) and the distributed `fasta2a_client.py` both instantiate `A2AClient(base_url="http://localhost:7000")` without API credentials. Production deployments MUST override the base URL to `https://` endpoints and fail-fast if a non-TLS origin is configured outside dev sandboxes.
2. **Secret sourcing** — `A2A_API_KEY` (and future client secrets) are injected only through the secrets manager backing the uv deployment. The adapter loads them at process start, stores only in memory, never echoes in logs/metrics, and exposes a fingerprinted hash solely for auditing. Missing secrets keep the client in network-gated mode without crashing.
3. **Header injection** — When `A2A_API_KEY` is present, the adapter MUST attach `Authorization: Bearer <token>` to every `send_message` and `get_task` call by registering the `a2a-sdk` `AuthInterceptor`. This logic lives alongside `fasta2a_client.py` so Feature 1 routing code remains unchanged.
4. **Rotation & revocation** — Secrets rotate at least every 60 days (or immediately during incidents). The adapter checks an optional `A2A_API_KEY_ISSUED_AT` timestamp to alert operators once secrets approach expiry and to stop startup when the value is older than 90 days.
5. **Future credentials** — Maintain an upgrade path for mutual TLS or request signing by reserving config fields (`A2A_CLIENT_CERT_PATH`, `A2A_HMAC_SECRET`). The adapter must validate that at least one authentication mechanism is configured before promoting to production; otherwise flag the deployment as "reduced trust" in health reports.

## Retry & Resiliency Requirements

- Classify upstream failures:
  - **Transient** (HTTP 5xx, connection resets, `canceled` states, JSON decoding errors). Action: automatically retry once after exponential backoff; include jitter ±200ms to avoid thundering herd.
  - **Fatal** (HTTP 4xx other than 429, upstream `failed/rejected`, schema validation issues caused by caller). Action: do not retry; surface descriptive error body plus correlation ID.
  - **Rate-limited (429)**: honor `Retry-After` header when provided; otherwise wait `A2A_RETRY_BACKOFF_SECONDS` before final retry.
- Total wall-clock budget per prompt (Telegram receive → Telegram reply) must remain ≤ 12s P95; abort A2A polling early if hitting this SLA so operators can re-issue prompts.
- Persona-aligned retry budgets:
  - Operator: 1 automatic retry with `A2A_RETRY_BACKOFF_SECONDS` base 2s and jitter ±200ms; `/retry` command may enqueue unlimited attempts provided queue depth ≤3.
  - OnCall: 1 automatic retry only when classified as transient and queue depth <2; `/retry` is allowed once and logs the escalation target.
  - IncidentCommander: 0 automatic retries; manual replay requires explicit `/retry <task_id>` plus `incident_id` echo so auditors can trace the override.
  - AutomationAuditor: 0 automatic retries and `/retry` command is rejected with a compliance reminder.
- Always return partial metadata even on failure so downstream tasks (architecture + backend) can reason about follow-up behavior.
 
## Latency & SLA Expectations

| Stage | Budget | Enforcement |
| --- | --- | --- |
| Telegram intake + sanitization | ≤200 ms | RouterCore timestamps update receipt and sanitization completion. |
| Adapter dispatch (`send_message`) | ≤500 ms median, 1s P95 | Capture HTTPX timing metrics from `fasta2a_client.py` instrumentation. |
| Polling window (`get_task` loop) | ≤2s median, 8s P95, hard 10s ceiling unless timeout override specified | `A2A_POLL_INTERVAL_SECONDS` + `A2A_MAX_POLLS` must be tuned so the loop cannot exceed 10s without raising `transient_error`. |
| Response normalization + Telegram reply | ≤1s | Includes formatting, metadata merge, and Telegram send call. |

- End-to-end SLO remains ≤2s median and ≤4s P95 under nominal load (matching Feature 1 acceptance metrics). When upstream latency trends beyond 4s P95 for ten minutes, raise a warning in metrics and annotate the Telegram status command output.
- IncidentCommander prompts must hold a tighter ceiling (≤2s P95) and pre-empt queue slots; if exceeded, surface a "priority_latency_breach" flag inside `/status` plus the affected `incident_id`.
- If A2A has not returned a terminal state by 10s, the adapter returns a holding reply (`"A2A still running"`) with the task ID and continues polling in the background up to the 12s overall SLA before canceling.
- Instrument `fasta2a_client` calls by capturing `send_message` and `get_task` duration via `httpx.Response.elapsed` and log them with `task_id`, `persona_tag`, and retry attempt so telemetry can attribute SLA regressions to either transport or upstream compute.
- Log `a2a.latency_ms` histograms alongside persona tags to detect whether certain personas (e.g., AutomationAuditor) are routinely slower.
 
## Confidentiality & Data Handling

- Only sanitized prompt text (post-router sanitization) is ever sent to `fasta2a_client.py`; redact TELEGRAM tokens, chat IDs, or other secrets from payload and logs.
- Mask usernames in structured logs using hashed surrogates while still passing cleartext to A2A. The hash algorithm (SHA-256 + salt) and salt rotation cadence must be documented so auditors can recompute identities when authorized.
- Encrypt every adapter-to-A2A hop in transit (TLS 1.2+) and rely on the existing uv runtime disk encryption for any temporary artifacts. No plaintext payloads may be written to `/tmp` or swap.
- Ensure `fasta2a_client.py` stores no local transcripts; responses remain in-memory and forwarded immediately back to Telegram. The adapter purges any cached `current_task` dictionaries once replies are delivered or retries exhausted.
- Restrict outbound network egress to Telegram + configured `A2A_BASE_URL`; log attempts to reach any other host and block the request. Health checks verify egress ACLs at startup.
- Apply least-privilege principle to API keys by scoping to read/write prompts only; rotate secrets quarterly or upon incident and notify operators if the key age exceeds the defined policy.
- Mirror Feature 1's hashed identity rules: store only SHA-256 + salt hashes for Telegram user IDs, On-Call handles, and new Incident Commander IDs inside adapter logs/metrics so audits can correlate activity without exposing PII.
- Record an `a2a_secret_fingerprint` derived from the API key hash inside `/status` output and purge it when redeploying to prevent drift between router + adapter secrets stores.
- Preserve persona tags, compliance tags, and metadata envelopes for 30 days inside the observability sink only; Telegram history remains the durable record. Any exported audit package must omit prompt text and instead include hashes plus metadata to honor confidentiality commitments.
 
## Observability & Metrics

- Emit structured log events `a2a.request`, `a2a.response`, and `a2a.failure` with correlation IDs, persona tags, latency_ms, attempt counts, and upstream status.
- Produce counters: `a2a_success_total`, `a2a_transient_error_total`, `a2a_fatal_error_total`, `a2a_retry_total` for SLO tracking.
- Capture histogram `a2a_latency_ms` bucketed at 0.5s increments up to 10s; feed into existing observability sink.
- Record final state + metadata inside Telegram reply (short form) so operators can escalate with consistent context.

## Acceptance Criteria & Deliverables
1. `output/34/feature2_architecture.md` consumers receive this document to derive interfaces without restating requirements.
2. Implementation stage can map every requirement to code/config (traceability table to be added during design).
3. Automated tests (Feature 2 testing task) can simulate both transient and fatal errors by referencing the retry policies defined here.
4. Documentation referencing confidentiality rules demonstrates how secrets and sanitized prompts flow through the system.

## Open Questions & Follow-Ups
- None — authentication, persona tags, and artifact media expectations were confirmed on 2025-11-18 (see decisions below).

## Decisions & Confirmations (2025-11-18)
1. **Authentication** — Reference implementations (`fasta2a_client.py`, `server_simple.py`, `server_mcp.py`) use unauthenticated HTTP inside a trusted network; keep `A2A_API_KEY` optional and omit Authorization headers when unset while preserving an AuthInterceptor-based upgrade path.
2. **Persona Tags** — Canonical personas now include `Operator`, `OnCall`, `IncidentCommander`, and `AutomationAuditor` per Feature 1 routing requirements; the adapter must reject or map any other persona label before dispatching to A2A.
3. **Artifact Media** — Upstream agents emit `TextPart` payloads only; treat responses as UTF-8 text and log + quarantine any future binary artifacts rather than attempting in-chat rendering.
