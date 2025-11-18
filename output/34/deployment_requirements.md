# Deployment & Configuration Requirements

## 1. Objective & Success Criteria
- Deliver a uv-managed Telegram relay that ships the same validated binaries across dev/stage/prod and keeps A2A turnaround <12s P95 with 99.5% successful message routing.
- Deployment processes must prove configuration parity (env diff automatically logged) and provide auditable trails for every credential change.
- Runtime must default to structured JSON logging, rate-limit enforcement, and deterministic shutdown handling to meet security and reliability objectives laid out in Feature 1 + 2 requirements.

## 2. Environment Matrix
| Environment | Purpose | Hosting Model | uv Launch Channel | Data & Access Controls |
| --- | --- | --- | --- | --- |
| **Local / Dev** | Fast-feedback for backend engineers + QA to validate flows against Telegram sandbox and mocked A2A. | Developer laptop or Codespaces using per-user `.env`. | `uv run bots/telegram_router.py --env-file .env` with hot reload disabled. | Use BotFather sandbox tokens, fake chat IDs, and stubbed `A2A_BASE_URL` pointing to mock server; logs stay local only. |
| **Staging** | Pre-production smoke region mirroring prod settings to validate infrastructure and integration changes. | Single container or VM managed by CI pipeline; secrets sourced from staging secret store. | CI deploy step runs `uv sync` then `uv run bots/telegram_router.py` under process supervisor (e.g., systemd, `uvx --from runit`). | Telegram Bot + chat IDs for staging-only chats, dedicated A2A tenant, restricted team VPN access, retained logs 14 days. |
| **Production** | Customer-facing relay with audited traffic and paging hooks. | HA pair of containers/pods behind private queue or orchestrator (Kubernetes, Nomad, or bare-metal service). | Image baked with `uv lock` + `uv export --format requirements-txt` for reproducibility; runtime uses `uv pip install --system` during build and `uv run bots/telegram_router.py`. | Tokens + chat IDs stored in managed vault (AWS Secrets Manager/GCP Secret Manager), egress limited to Telegram + `A2A_BASE_URL`, logs streamed to SIEM for 90 days. |

## 3. uv Runtime & Process Supervision
- Python 3.11 baseline; `uv` lockfile checked in and promoted through environments.
- Deployable artifact contains `uv` binary, `.python-version`, and lockfile; CI step verifies `uv hash` to detect tampering.
- Every runtime executes health probe `uv run bots.telegram_router --check-config` (requires CLI shim) before entering polling loop; failure aborts deployment.
- Supervisors (systemd, Kubernetes sidecar, or Procfile) must send SIGTERM and allow 30s drain so the router can stop polling, finish queue drain, and flush logs.
- Horizontal scaling: additional instances allowed only when `TELEGRAM_CHAT_ID` scope expands; otherwise keep singleton to avoid duplicate replies (long polling uniqueness requirement).

## 4. Configuration & Secrets Handling
### 4.1 Secret Catalog & Storage Expectations
| Secret | Description | Storage Rules | Rotation Policy |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Credentials from BotFather for each environment. | Keep in secret manager; mount into runtime env vars only at process start; never baked into images. | 90-day rotation; revoke old token immediately; record change ticket ID. |
| `TELEGRAM_CHAT_ID` | Authorized chat identifier(s). | Non-secret but treat as configuration-controlled; maintain allow-list file committed to repo and hashed at deploy time. | Update only through change request linked to stakeholder approval. |
| `A2A_API_KEY` (optional) | Upstream auth token if required. | Secret manager with envelope encryption; inject via runtime env var; forbid logging. | Align with upstream policy (default 180 days) and coordinate with A2A owners. |

### 4.2 Configuration Contract
- Non-secret variables (`TELEGRAM_POLL_TIMEOUT`, `TELEGRAM_MAX_CONCURRENCY`, retry knobs, persona tags) live in `.env.example` and are surfaced via deployment manifests per environment.
- ConfigGuard in `bots/telegram_router.py` must run on boot; deployments fail fast when required vars missing or invalid.
- Environment promotion requires `config diff` step: CI compares staging vs prod env var sets and blocks drift >5% (any missing secret or changed value without ticket ID is rejected).
- Provide `config manifest` artifact (YAML) per deployment summarizing key/value (secret values masked) plus checksum of `.env` to support auditability.

### 4.3 Secrets Delivery Flow
1. CI/CD retrieves secrets via workload identity and templates `.env.runtime`.
2. `uv run bots/telegram_router.py` is invoked with `--env-file /run/secrets/.env.runtime` or supervisor exports env vars before exec.
3. Runtime never writes secrets to disk; crash dumps scrub values before shipping to logs.

## 5. Runtime Observability Requirements
### 5.1 Logging
- Structured JSON logs already emitted by router; deployment must route stdout/stderr to centralized collector (CloudWatch Logs, Stackdriver, or ELK) with timezone-synchronized timestamps.
- Mandatory fields: `event`, `correlation_id`, `persona_tag`, `chat_id_hash`, `status`, `latency_ms`, `env`. Supervisors append `env` + `build_sha` automatically.
- Log retention: dev (local only), staging 14 days, prod 90 days with immutability + access control (least privilege for on-call team).

### 5.2 Metrics & Alerts
- Export metrics via OTLP/Prometheus sidecar or StatsD sink: queue depth, Telegram/A2A latency histograms, retry counts, error classifications, process uptime.
- Define SLOs: <12s P95 round-trip latency, <0.5% transient failure rate, zero unauthorized chat attempts per day.
- Alert thresholds: `router.rate_limited` >10/min triggers warning; `a2a.failure{classification="fatal"}` >3 in 5 minutes pages on-call; `transport.retry` stuck >5 minutes indicates Telegram outage.

### 5.3 Tracing & Audit
- Optional OpenTelemetry spans must be enabled via `OTEL_EXPORTER_OTLP_ENDPOINT` env var; deployments set this in staging/prod to feed into trace backend.
- Maintain deployment audit log capturing: build SHA, uv lock checksum, config manifest checksum, and operator ID; store alongside release notes.

## 6. Security & Compliance Guardrails
- Principle of least privilege networking: only egress to `api.telegram.org` and configured `A2A_BASE_URL`; outbound firewall enforced via security groups or Kubernetes NetworkPolicy.
- Container/VM must run as non-root, drop `CAP_NET_RAW`, and enable read-only root filesystem except for `/tmp` scratch (required by uv caches).
- Enable periodic vulnerability scans on uv lockfile (SCA) and base image; block deployment on critical CVEs affecting runtime dependencies.
- Backup/restore: capture daily encrypted snapshot of `.env.runtime` template (without secret values) and deployment manifests to support DR reviews.
