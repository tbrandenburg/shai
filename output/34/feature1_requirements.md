# Feature 1 — Telegram Routing Requirements

## Source Inputs
- Issue #34 conversation (`output/34/issue_conversation.md`) requesting a uv-based Telegram bot that forwards messages to the upstream `fasta2a_client.py` agent and returns responses to the originating Telegram chat.
- Configuration parameters provided by the deployment environment: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

## Business Objectives
1. Allow authorized Telegram users inside a controlled chat to send prompts through a uv-based bot and receive responses from the A2A agent/network without leaving Telegram.
2. Ensure only pre-approved chats/users are serviced, preserving confidentiality while maintaining traceability between Telegram requests and A2A responses.
3. Provide an auditable, low-latency routing layer that can expand to additional personas or upstream agents in future releases.

## Authorized User Personas
| Persona | Description | Primary Goals | Authorization Rules |
| --- | --- | --- | --- |
| **A2A Operator** | Maintains and monitors upstream A2A workflows and the associated uv infrastructure. | Validate Telegram prompts versus upstream responses, escalate anomalies, and confirm SLA compliance dashboards. | Must originate from the configured `TELEGRAM_CHAT_ID`; privileged `/status` and `/flush` commands restricted to an operator allowlist tracked by Telegram user ID for audit trails. |
| **On-Call Responder** | Provides 24/7 coverage when Operators are offline. | Keep the conversation flowing, trigger retries, and confirm the router is reachable during incidents. | Shares the same chat-level authorization but is throttled to core commands (`prompt`, `retry`, `help`). The router captures Telegram user ID + timestamp for every message to preserve accountability. |
| **Automation Auditor (Future)** | Reviews transcripts for policy/compliance insights. | Pull structured transcripts and verify adherence to confidentiality promises. | Read-only for now; requirements drive backlog work for export tooling but no bot interaction is permitted in this release. |

## Conversation Flows
1. **Authorized Prompt Flow (Happy Path)**
   - Authorized user sends a message inside the allowed Telegram chat.
   - Bot validates `TELEGRAM_CHAT_ID`, sanitizes input, and forwards payload to `fasta2a_client.py` over uv event loop.
   - Bot receives response payload, formats it (including any status metadata), and replies back within the same chat thread.
2. **Unauthorized Chat/User Attempt**
   - Bot receives message from a chat/user whose ID does not match `TELEGRAM_CHAT_ID`.
   - Bot declines processing, logs the attempt with timestamp and IDs, and optionally replies with a friendly denial message (no forwarding occurs).
3. **Upstream Agent Error / Timeout**
   - A2A client raises error or exceeds SLA.
   - Bot communicates failure with actionable details (error summary, retry guidance) to the user, records the incident, and optionally retries based on policy.
4. **Configuration or Connectivity Fault**
   - Missing/invalid env vars or Telegram connectivity failure is detected on startup or during polling/webhook dispatch.
   - Bot emits structured logs, notifies operators (via fallback channel or pinned status message), and refuses to accept messages until resolved.

## Conversation Limits & Guardrails
- **Message payload:** Enforce a 2,000-character (UTF-8) maximum after sanitization to stay well below Telegram's 4,096 limit and avoid HTTP 413 responses when forwarding to `fasta2a_client.py`.
- **Outstanding requests:** Only one in-flight A2A task per `TELEGRAM_CHAT_ID` is allowed because the upstream client polls synchronously until a final state is reached; queue subsequent prompts and reply with a "router busy" notice that includes the queued position.
- **Rate limiting:** Apply a rolling limit of six prompts per user per minute with exponential backoff after the third violation to protect Telegram and A2A APIs from flooding.
- **Conversation window:** Persist the last 25 prompt/reply pairs (ID, timestamp, persona tag) in memory for correlation IDs and manual replay while deferring durable storage to future scope.
- **Attachment policy:** Text-only messages are accepted for this release; strip any media attachments, acknowledge the omission, and guide the sender to paste textual context instead.

## Security & Configuration Constraints
- `TELEGRAM_BOT_TOKEN`
  - Pulled exclusively from the deployment secrets manager or CI-injected runtime env; never written to disk or echoed in logs/metrics.
  - Validate format on startup (`^\d+:[A-Za-z0-9_-]{35,}$`), fail-fast with a redacted error if the token is malformed or missing.
  - Rotate at least every 90 days and immediately on incident response; expose a `/healthz` probe field indicating token age to help SREs enforce rotation SLAs.
  - Hold the token only in memory, scrubbed when the process exits, and gate any debugging CLI to prevent accidental exposure.
- `TELEGRAM_CHAT_ID`
  - Configured per environment (dev/stage/prod) via env var or secrets provider and never hard-coded; maintain a runbook entry for retrieving the numeric ID.
  - Verify the chat ID for every incoming update, emit a `SECURITY_DENIED` structured log for mismatches, and hash the ID (`sha256`) before persisting to logs/metrics to avoid leaking the raw value.
  - Allow a comma-separated override list for future multi-chat support but enforce single-ID mode in this release with a config guard.
- Additional safeguards
  - Input data is sanitized (trim, collapse whitespace, strip HTML) before reaching `fasta2a_client.py`; reject payloads containing tokens, secrets, or binary blobs.
  - Every routing decision logs masked identifiers, persona tag, correlation ID, and A2A task ID so the business can prove traceability during audits.
  - The uv process runs under least-privilege IAM with outbound networking locked to Telegram + the A2A host; health telemetry avoids embedding secrets while still proving liveness.

## Acceptance Metrics
| Metric | Target | Measurement Method | Notes |
| --- | --- | --- | --- |
| Authorization accuracy | 100% of processed messages originate from the configured `TELEGRAM_CHAT_ID`; zero unauthorized routings per week. | Compare Telegram update chat IDs versus the configured ID in structured logs; alert on any mismatch. | Demonstrates that chat gating plus hashed logging works.
| Latency (P50 / P95) | ≤2s median, ≤4s 95th percentile for Telegram → A2A → Telegram round-trips. | Capture timestamps at receipt, dispatch to `fasta2a_client.py`, and reply; compute percentiles daily. | Aligns with operator expectation for "near real-time" replies.
| Reliability | ≥99.5% of routed messages deliver a response or actionable error within SLA each week. | Count success/error events in metrics pipeline; exclude unauthorized attempts. | Ensures queueing/ retry logic hides upstream flakiness. |
| Rate-limit compliance | ≤1% of prompts throttled due to rate limiting under normal operations. | Monitor throttling counters per persona. | Confirms limits are tuned for real workflows while protecting upstream APIs. |
| Observability coverage | 100% of routed messages include correlation ID, persona tag, Telegram user ID hash, and A2A task ID in logs. | Automated log sampling + schema validation. | Required for audit readiness and Automation Auditor persona. |
| Operator satisfaction | ≥4/5 average satisfaction score gathered bi-weekly from Operators + On-Call responders. | Lightweight pulse survey captured via shared form. | Confirms the conversational experience meets stakeholders’ needs. |

## Assumptions & Open Questions
- Only a single Telegram chat is supported in the initial release; scaling to multiple IDs will require configuration schema updates.
- Persistence of transcripts is deferred; current design assumes Telegram history suffices, but auditors may request exports later.
- Need confirmation whether Telegram webhook or long-polling will be used for uv integration (to be detailed by API Designer in the next task).
- Validate with stakeholders that the six-prompts-per-minute limit and single in-flight task queue satisfy bursty incident workflows; adjust thresholds if they anticipate higher concurrency.
