# Feature 2 — A2A Integration Requirements

## Source Inputs
- Issue #34 context and conversation (`output/34/issue_conversation.md`) requesting a uv-based Telegram bot that proxies prompts to the upstream `fasta2a_client.py` agent and returns results to the authorized chat.
- Feature 1 deliverables: routing requirements (`output/34/feature1_requirements.md`), architecture notes (`output/34/feature1_architecture.md`), backend design (`docs/telegram_routing_design.md`), and implemented bot (`bots/telegram_router.py`).
- Upstream reference implementation (`pydanticai-a2a` repo) where `fasta2a_client.py` constructs an `A2AClient`, issues `send_message` calls, and polls task status via HTTPX (`run_client.py`).

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
- `AutomationAuditor` — Read-only oversight role; prompts flagged with this tag should never request mutative operations and may be throttled upstream.

Treat these three tags as the canonical `A2A_ALLOWED_PROMPT_TAGS` default. Reject or translate any other persona labels before dispatch so upstream guardrails stay deterministic.

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
 
## Authentication Model Confirmation
- The upstream reference agent defined in `server_simple.py`/`server_mcp.py` (tbrandenburg/pydanticai-a2a) and the distributed `fasta2a_client.py` both instantiate `A2AClient(base_url="http://localhost:7000")` without any API credentials, confirming that the current deployment relies on network isolation rather than request-level tokens.
- Treat `A2A_API_KEY` as optional: when unset, omit Authorization headers entirely and depend on Telegram chat gating plus VPC egress controls for security.
- Maintain an upgrade path by wiring the adapter to accept a bearer/API key header using the `a2a-sdk` `AuthInterceptor` scheme (per https://a2a-protocol.org/latest/sdk/python/api/a2a.client). Once secrets are issued, the same env var can toggle credentialed calls without code edits.

## Retry & Resiliency Requirements

- Classify upstream failures:
  - **Transient** (HTTP 5xx, connection resets, `canceled` states, JSON decoding errors). Action: automatically retry once after exponential backoff; include jitter ±200ms to avoid thundering herd.
  - **Fatal** (HTTP 4xx other than 429, upstream `failed/rejected`, schema validation issues caused by caller). Action: do not retry; surface descriptive error body plus correlation ID.
  - **Rate-limited (429)**: honor `Retry-After` header when provided; otherwise wait `A2A_RETRY_BACKOFF_SECONDS` before final retry.
- Total wall-clock budget per prompt (Telegram receive → Telegram reply) must remain ≤ 12s P95; abort A2A polling early if hitting this SLA so operators can re-issue prompts.
- Always return partial metadata even on failure so downstream tasks (architecture + backend) can reason about follow-up behavior.

## Confidentiality & Data Handling
- Only sanitized prompt text (post-router sanitization) is ever sent to `fasta2a_client.py`; redact TELEGRAM tokens, chat IDs, or other secrets from payload and logs.
- Mask usernames in structured logs using hashed surrogate while still passing cleartext to A2A (required for auditing but never logged).
- Ensure `fasta2a_client.py` stores no local transcripts; responses remain in-memory and forwarded immediately back to Telegram.
- Restrict outbound network egress to Telegram + configured `A2A_BASE_URL`; log attempts to reach any other host.
- Apply least-privilege principle to API keys by scoping to read/write prompts only; rotate secrets quarterly or upon incident.

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
2. **Persona Tags** — Canonical personas remain `Operator`, `OnCall`, and `AutomationAuditor` per Feature 1 routing requirements; the adapter must reject or map any other persona label before dispatching to A2A.
3. **Artifact Media** — Upstream agents emit `TextPart` payloads only; treat responses as UTF-8 text and log + quarantine any future binary artifacts rather than attempting in-chat rendering.
