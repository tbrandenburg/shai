# Deployment & Configuration Requirements

## 1. Objective & Success Criteria
- Deliver a uv-managed Telegram relay that ships the same validated binaries across dev/stage/prod and keeps A2A turnaround <12s P95 with 99.5% successful message routing.
- Deployment processes must prove configuration parity (env diff automatically logged) and provide auditable trails for every credential change.
- Runtime must default to structured JSON logging, rate-limit enforcement, and deterministic shutdown handling to meet security and reliability objectives laid out in Feature 1 + 2 requirements.

## 2. Environment Matrix
| Environment | Purpose | Hosting Model & Artifact Strategy | uv Launch Channel | Secrets & Access Controls | Observability Coverage |
| --- | --- | --- | --- | --- | --- |
| **Local / Dev** | Fast-feedback for backend engineers + QA to validate flows against Telegram sandbox and mocked A2A. | Developer laptop or Codespaces cloning repo, pinning to the exact `uv.lock`. Engineers run `uv sync` per branch and cache `uv toolchain` locally for reproducible virtualenvs. | `uv run bots/telegram_router.py --env-file .env` with hot reload disabled; optional `uv run bots/telegram_router.py --check-config` before hacking. | Use BotFather sandbox tokens, fake chat IDs, stubbed `A2A_BASE_URL`, and developer-owned `.env`; secrets never leave workstation. Access controlled through repo membership. | Structured JSON logs stay on console; optional `uv run scripts/pipeline_task_machine.sh` disabled. Metrics printed locally only; no remote collectors allowed. |
| **Staging** | Pre-production smoke region mirroring prod settings to validate infrastructure and integration changes. | Single container or VM created by CI pipeline (Containerfile + `uv export`), storing artifacts in staging registry. Secrets pulled via CI workload identity. | CI deploy stage runs `uv sync --locked` then `uv run bots/telegram_router.py` under supervisor (systemd service, `uvx --from runit`, or `Procfile` entry). Health check gate must pass before traffic is allowed. | Telegram Bot + chat IDs for staging-only chats, dedicated A2A tenant, restricted VPN, rotation tracked in staging vault. Only release engineers may read secrets; all env vars templated through `.env.runtime`. | Logs forwarded to staging log drain (CloudWatch/Stackdriver) with 14-day retention, OTEL spans sampled at 25%, Prometheus/StatsD sidecar enabled for latency + queue depth gauges. |
| **Production** | Customer-facing relay with audited traffic and paging hooks. | HA pair of containers/pods scheduled via orchestrator (Kubernetes/Nomad) referencing immutable OCI image built from `uv lock` + `uv export`. Build pipeline runs `uv hash` and signs manifest. | Runtime container executes `uv pip install --system` during image build, ships `uv` binary inside image, and launches `uv run bots/telegram_router.py` under process supervisor with readiness probes. | Tokens, chat IDs, persona map, and A2A secrets stored in managed vault (AWS Secrets Manager, GCP SM) and injected at start via encrypted files or env; egress locked to Telegram + `A2A_BASE_URL`. Access requires break-glass approval. | Logs streamed to SIEM for 90 days, traces exported to OTLP backend with 100% sampling on fatal spans, metrics scraped by production Prometheus and mirrored to alerting platform (PagerDuty hooks). |

### 2.1 Promotion Gates & Traceability
- **Dev → Staging:** requires green `pytest` suites (`tests/test_telegram_routing.py`, `tests/test_a2a_adapter.py`), `uv hash` match, and configuration diff report archived in `output/34/deployment_test_report.md`.
- **Staging → Production:** add security scan evidence (container scan + `uv lock` SCA), sign config manifest checksum, and capture operator approval ID.
- Every deployment artifact (image digest + `uv.lock` checksum) must be logged inside the deployment logbook with timestamp, triggering commit SHA, and person initiating promote.
- Drift detection is mandatory: CI blocks promotion if staging/prod env variable sets differ (excluding secrets) by >5% or if extra tokens exist without recorded ticket ID.

## 3. uv Runtime & Process Supervision
- Python 3.11 baseline; `uv` lockfile checked in and promoted through environments.
- Deployable artifact contains `uv` binary, `.python-version`, and lockfile; CI step verifies `uv hash` to detect tampering.
- Every runtime executes health probe `uv run bots.telegram_router --check-config` (requires CLI shim) before entering polling loop; failure aborts deployment.
- Supervisors (systemd, Kubernetes sidecar, or Procfile) must send SIGTERM and allow 30s drain so the router can stop polling, finish queue drain, and flush logs.
- Horizontal scaling: additional instances allowed only when `TELEGRAM_CHAT_ID` scope expands; otherwise keep singleton to avoid duplicate replies (long polling uniqueness requirement).

### 3.1 Capacity & Scaling Guardrails
- **Baseline load model:** 30 inbound prompts/minute with burst tolerance of 2× for 5 minutes; router queue depth set to 25 with single in-flight A2A call enforced by semaphore.
- **Vertical sizing targets:** request 500m CPU + 512 MiB memory per instance; autoscaler may increase to 1 vCPU / 1 GiB when `queue.wait_ms` p95 exceeds 4 s for 3 consecutive intervals.
- **Active/standby rule:** production keeps two pods, but only one handles Telegram polling. Second pod must run in passive mode (poller disabled) and activates only under manual failover to maintain single consumer semantics.
- **Throughput verification:** before scaling past one active poller, engineers must demonstrate `TELEGRAM_CHAT_ID` sharding (multiple bots or chats) plus deterministic offset partitioning documented inside deployment architecture.
- **Back-pressure contract:** if CPU >60% or `latency.round_trip_ms` P95 >12s, orchestrator must first increase `RATE_LIMIT_PER_MINUTE` guardrails downward (throttle) before adding compute to avoid violating Telegram policies.
- **Disaster recovery:** cold standby environment must be restored within 30 minutes by replaying the latest signed config manifest + `uv lock` artifact; test this quarterly.

## 4. Configuration & Secrets Handling
### 4.1 Secret Catalog & Storage Expectations
| Secret / Sensitive Config | Description | Storage Rules | Rotation Policy | Notes |
| --- | --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot credential issued per environment. | Vault-backed env var; decrypted in memory only; never emitted to logs or crash dumps. | 90-day rotation; record ticket ID and revoke previous token immediately. | BotFather access limited to platform owner. |
| `TELEGRAM_CHAT_ID_ALLOWLIST` | Immutable list of authorized chats/users. | Store hashed list in repo + runtime copy in vault; compare checksum during deploy. | Update requires security sign-off and chat owner approval. | Not secret but regulated configuration. |
| `A2A_API_KEY` | Credential for upstream adapter. | Vault secret with envelope encryption; runtime loads via `/run/secrets/.env.runtime`. | 180-day rotation or sooner if upstream revokes; coordinate with A2A ops. | Must never be echoed into telemetry. |
| `A2A_BASE_URL` & SSL material | Target endpoint + optional client certs. | Non-secret URL stored in config manifest; client cert/private key stored in vault/KMS-backed files. | URL change tied to release record; certificates rotated 60 days before expiry. | Validate TLS fingerprints at boot. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` + auth token | Tracing/metrics sink credentials. | Keep endpoint config public but token inside vault; inject via env var on staging/prod only. | 180-day rotation plus revocation after incident. | Dev env uses mock endpoint. |
| `LOG_DRAIN_TOKEN` (Datadog/Splunk/API key) | Grants write access to centralized logging. | Store as secrets manager entry; mount as file with 0400 permissions. | 90-day rotation coordinated with observability team. | Rotation automatically restarts collector sidecar. |
| `CONFIG_MANIFEST_SIGNATURE` | Private key (or KMS alias) that signs config manifest checksum. | Resides only in KMS; CI requests ephemeral signing operation; never exported. | Annual rotation w/ dual-control change record. | Required before staging→prod promotion. |

### 4.2 Configuration Contract
- Non-secret variables (`TELEGRAM_POLL_TIMEOUT`, `TELEGRAM_MAX_CONCURRENCY`, retry knobs, persona tags) live in `.env.example` and are surfaced via deployment manifests per environment.
- ConfigGuard in `bots/telegram_router.py` must run on boot; deployments fail fast when required vars missing or invalid.
- Environment promotion requires `config diff` step: CI compares staging vs prod env var sets and blocks drift >5% (any missing secret or changed value without ticket ID is rejected).
- Provide `config manifest` artifact (YAML) per deployment summarizing key/value (secret values masked) plus checksum of `.env` to support auditability.

### 4.3 Secrets Delivery Flow
1. CI/CD retrieves secrets via workload identity and templates `.env.runtime`.
2. `uv run bots/telegram_router.py` is invoked with `--env-file /run/secrets/.env.runtime` or supervisor exports env vars before exec.
3. Runtime never writes secrets to disk; crash dumps scrub values before shipping to logs.

#### 4.4 Secret Verification & Incident Handling
- Prior to deploy, CI verifies vault versions for every required secret and fails if any entry is older than its policy allows.
- Deployment pipeline stores a SHA-256 hash of the rendered `.env.runtime` (with secret values redacted) inside the audit log alongside deploy ID.
- On suspected leak, operations must rotate the impacted secret, invalidate every running token via Telegram/A2A consoles, and attach incident ID to the config manifest before re-deploying.
- Vault access logs are reviewed weekly; anomalies trigger business-analyst review plus security follow-up within 24 hours.

## 5. Runtime Observability Requirements
### 5.1 Logging
- Structured JSON logs already emitted by router; deployment must route stdout/stderr to centralized collector (CloudWatch Logs, Stackdriver, or ELK) with timezone-synchronized timestamps.
- Mandatory fields: `event`, `correlation_id`, `persona_tag`, `chat_id_hash`, `status`, `latency_ms`, `env`. Supervisors append `env` + `build_sha` automatically.
- Log retention: dev (local only), staging 14 days, prod 90 days with immutability + access control (least privilege for on-call team).

### 5.2 Metrics & Alerts
- Export metrics via OTLP/Prometheus sidecar or StatsD sink: queue depth, Telegram/A2A latency histograms, retry counts, error classifications, process uptime.
- Define SLOs: <12s P95 round-trip latency, <0.5% transient failure rate, zero unauthorized chat attempts per day.
- Alert thresholds: `router.rate_limited` >10/min triggers warning; `a2a.failure{classification="fatal"}` >3 in 5 minutes pages on-call; `transport.retry` stuck >5 minutes indicates Telegram outage.

| Metric Name | Type | Description | Target/SLO | Dashboard Owner |
| --- | --- | --- | --- | --- |
| `latency.round_trip_ms` | Histogram | Telegram receive → reply duration, tagged by env, persona, command. | P95 < 12s, P99 < 20s. | DevOps dashboard `telegram_router_latency`. |
| `queue.depth` | Gauge | Number of prompts waiting inside QueueManager. | Average < 5, never > 20 for >2 minutes. | NOC wallboard. |
| `a2a.failure_total` | Counter | Failures classified as transient or fatal from `services/a2a_adapter`. | Fatal < 3 per 5 min; transient < 0.5% of traffic. | Incident response board. |
| `router.uptime_seconds` | Counter | Seconds since process start; resets on crash/restart. | Alert if reset >1/day outside deployments. | Platform SRE sheet. |
| `rate_limit.hit` | Counter | Per-persona rate limit denials. | <10 per persona per 12h; more implies misconfiguration. | Business analyst adoption report. |

- Dashboards must visualize histograms + counters with per-environment filters and include annotations for deployments (commit SHA + operator).

### 5.3 Tracing & Audit
- Optional OpenTelemetry spans must be enabled via `OTEL_EXPORTER_OTLP_ENDPOINT` env var; deployments set this in staging/prod to feed into trace backend.
- Maintain deployment audit log capturing: build SHA, uv lock checksum, config manifest checksum, and operator ID; store alongside release notes.

### 5.4 Observability Deliverables by Environment
- **Dev:** run with `LOG_LEVEL=DEBUG`, export metrics locally using `uv run bots/telegram_router.py --emit-metrics stdout`, and capture trace samples only when debugging specific issues.
- **Staging:** enable full logging + 25% tracing, configure Prometheus scraping, and attach dashboards/screenshots to every change request showing the metrics table above for at least 30 minutes of soak.
- **Production:** enforce immutable log streaming, 100% fatal-span tracing, real-time dashboards with PagerDuty hooks, and nightly export of key metrics (`latency.round_trip_ms`, `a2a.failure_total`, `queue.depth`) into the BI warehouse for KPI review.

## 6. Security & Compliance Guardrails
- Principle of least privilege networking: only egress to `api.telegram.org` and configured `A2A_BASE_URL`; outbound firewall enforced via security groups or Kubernetes NetworkPolicy.
- Container/VM must run as non-root, drop `CAP_NET_RAW`, and enable read-only root filesystem except for `/tmp` scratch (required by uv caches).
- Enable periodic vulnerability scans on uv lockfile (SCA) and base image; block deployment on critical CVEs affecting runtime dependencies.
- Backup/restore: capture daily encrypted snapshot of `.env.runtime` template (without secret values) and deployment manifests to support DR reviews.
