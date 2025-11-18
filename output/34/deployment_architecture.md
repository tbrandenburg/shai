# Deployment Architecture Plan

## Objective & Scope
Translate the deployment requirements into an actionable architecture that governs uv-based runtime supervision, deterministic configuration sourcing, reproducible artifact packaging, and tightly gated promotion flows across dev, staging, and production. Inputs include `output/34/deployment_requirements.md`, Feature 1/2 assets, implemented router/adapters, and the approved observability + security guardrails.

## System Overview
- **Artifact of record**: An immutable OCI image (or tarball for legacy VMs) that embeds the uv binary, `.python-version`, `uv.lock`, `bots/telegram_router.py`, `services/a2a_adapter.py`, and launcher shims. The image digest + `uv lock` checksum form the promotion key.
- **Runtime contract**: Every entrypoint invokes `uv run bots/telegram_router.py --check-config` before starting the long-poll loop, exports structured JSON logs, and exposes `/healthz` once Telegram and A2A reachability succeed.
- **Supervision fabric**: Local dev uses direct `uv run`; staging and production enforce supervisors (systemd, runit, Procfile worker, or Kubernetes Deployment) that deliver SIGTERM with a 30s grace, restart with capped back-off, and annotate logs with env/build metadata.

## Environment Topologies
| Environment | Artifact Source | Supervision & Launch | Config & Secrets | Observability & Scaling |
| --- | --- | --- | --- | --- |
| **Local / Dev** | `uv sync --locked` on workstation; optional `uv export` cache. | Direct `uv run bots/telegram_router.py --env-file .env`; optional `just dev:router`. Hot reload disabled to match lockfile. | `.env` checked out from repo plus sandbox tokens managed per developer. Secrets never leave workstation. | Logs stay on console; metrics/traces stdout only. Single process, no scaling. |
| **Staging** | CI builds Containerfile (`uv export --format requirements.txt` + `pip install --no-deps`), pushes image to staging registry. | Systemd unit, runit service, or Procfile dyno launches `uv run ... --env-file /run/secrets/.env.runtime`. Supervisor restarts crashes and emits heartbeat metrics. | CI renders `.env.runtime` from staging vault, stores SHA-256 + ticket ID, and injects via tmpfs. Config diff ensures parity with production minus secret values. | Structured logs ship to staging log drain; OTEL tracing at 25%; Prometheus sidecar scrapes metrics. Single active instance for Telegram polling. |
| **Production** | Same digest promoted from staging registry; cosign signature verified, `uv hash` rechecked. | Kubernetes Deployment (2 replicas, 1 active poller/1 passive) or HA VM pair; readiness probe hits `/healthz`, preStop waits 30s, liveness restarts on stall. Active/standby semantics enforced via feature flag in config manifest. | Secrets pulled from managed vault (AWS SM/GCP SM) using workload identity; persona map + non-secret config versioned in git manifest. Drift detection blocks deploy if env var sets diverge >5%. | Logs to SIEM (90 days), OTEL fatal-span sampling 100%, Prometheus metrics with PagerDuty alerts. Autoscaler obeys queue depth + latency guardrails before adding compute. |

## Process Supervision & Capacity Controls
1. **Lifecycle hooks**: `/healthz` only returns 200 once ConfigGuard passes and Telegram/A2A handshake succeeds. Supervisors gate traffic on this signal.
2. **Drain protocol**: PreStop (Kubernetes) or systemd `ExecStop` sends SIGTERM, waits 30s, and cancels long poll to avoid duplicate replies. Router confirms queue depth zero before exit.
3. **Crash safety**: Supervisors limit restart bursts to 5 attempts/15 minutes and emit `router.uptime_seconds` counters for monitoring.
4. **Scaling template**: Default request 500m CPU / 512 MiB; autoscaler can bump to 1 vCPU / 1 GiB when `queue.wait_ms` or `latency.round_trip_ms` alarms fire. Additional pollers require documented Telegram chat sharding plus offset coordination stored in architecture doc.
5. **Back-pressure failsafe**: When CPU >60% or latency P95 >12s, orchestrator first throttles via config (`RATE_LIMIT_PER_MINUTE`, queue depth) before provisioning new compute, honoring Telegram policy constraints.

## Artifact Packaging & Supply Chain
1. **Build stage**
   - Trigger: merge or release tag.
   - Steps: `uv lock --frozen` validation → `uv export --format requirements.txt` → Containerfile installs uv + dependencies → copy repo, `.python-version`, configs.
   - Output: OCI image digest + `uv lock` checksum captured in CI metadata.
2. **Security & signing**
   - Run SCA against `uv.lock`, container vulnerability scan (Trivy/Grype), and `uv hash` tamper check.
   - Sign image with cosign + attach provenance (SLSA attestation) referencing git SHA and pipeline ID.
3. **Artifact registry**
   - Dev/staging share staging registry; prod pulls from immutable prod registry fed only via promotion job.
   - Drift detection ensures staging/prod image digests match; mismatch blocks deploy.
4. **Runtime bundle**
   - Deployments mount read-only file system, keeping uv caches in `/tmp` only.
   - `config-manifest.yaml` and signed checksum accompany artifact for audit replay and DR restoration.

## Configuration & Secret Distribution
1. **Source of truth**: `.env.example` documents non-secret defaults; `config/environments/*.yaml` (git) lists per-env overrides; secret catalog maintained in vault with rotation policies (90/180 days, etc.).
2. **Templating engine**: CI uses env-aware Jinja/ytt templates to merge manifest + secrets, output `/run/secrets/.env.runtime`, and produce a redacted diff stored with deploy logs.
3. **Verification**: `uv run bots/telegram_router.py --check-config` validates required vars, persona map hash, and Telegram chat allowlist checksum. Failure aborts deploy.
4. **Parity enforcement**: `config diff` compares staging vs production manifests (excluding values) and blocks >5% drift or missing keys; operator must attach ticket ID for every intentional change.
5. **Incident hooks**: On suspected leak, rotation pipeline invalidates tokens, regenerates `.env.runtime`, increments manifest version, and re-runs deploy with incident ID appended.

## Promotion Flow & Gates
1. **Dev → Staging**
   - Preconditions: green `pytest tests/test_telegram_routing.py` + `tests/test_a2a_adapter.py`, passing lint, successful container + SCA scans, config diff vs template.
   - Actions: Deploy staging image, run smoke script hitting Telegram sandbox + mocked A2A, verify `/healthz`, soak for 30 minutes while collecting latency + queue depth metrics.
   - Evidence: Upload log excerpts, metrics screenshots, and rendered config diff to `output/34/deployment_test_report.md`.
2. **Staging → Production**
   - Additional gates: container scan rerun on final digest, config manifest signed via KMS key referenced as `CONFIG_MANIFEST_SIGNATURE`, operator approval ID recorded, drift check vs production secrets.
   - Deployment: GitOps job updates production manifest referencing same artifact digest and secret versions. Kubernetes path performs rolling update (maxUnavailable=1); VM path executes blue/green toggling load balancer after passive node passes health checks.
3. **Post-deploy & rollback**
   - Monitoring: P95 latency <12s, `a2a.failure_total{classification="fatal"}` <3/5m, `rate_limit.hit` <10/persona/12h. Automated alerts escalate via PagerDuty.
   - Rollback triggers: SLO breach, config diff failure, or incident flag. GitOps reverts commit or redeploys previous artifact+manifest pair using stored checksums.

## Observability & Audit Architecture
- **Logging**: Supervisors stream stdout/stderr to environment-specific sinks (dev console, staging log drain 14d, prod SIEM 90d). Mandatory fields include `event`, `correlation_id`, `chat_id_hash`, `persona_tag`, `status`, `latency_ms`, `env`, and `build_sha`.
- **Metrics**: Prometheus/StatsD exporters emit `latency.round_trip_ms`, `queue.depth`, `a2a.failure_total`, `router.uptime_seconds`, and `rate_limit.hit`. Dashboards annotate deployments using config manifest ID and git SHA.
- **Tracing**: OpenTelemetry exporters enabled via `OTEL_EXPORTER_OTLP_ENDPOINT`; staging samples at 25%, prod captures 100% of fatal spans. Spans tag persona, env, Telegram update offset, and A2A classification.
- **Audit trail**: Deployment job logs include artifact digest, `uv lock` checksum, config manifest checksum, operator + approval IDs, secret version numbers, and promotion timestamps. Entries stored alongside release notes for DR replay.

## Security & Compliance Controls
- Non-root runtime, read-only root FS, drop `CAP_NET_RAW`, and limit egress to `api.telegram.org` + `A2A_BASE_URL` via NetworkPolicy/Security Group.
- Automated scanning on every commit plus nightly re-scan of released images; pipeline blocks on critical CVEs.
- Secrets rotation cadence enforced by CI preflight; failure to meet cadence blocks promotion.
- Disaster recovery: cold standby instructions reference latest signed config manifest + uv artifact; restore target <30 minutes validated quarterly.
- Documentation-as-code: this architecture, manifests, runbooks, and test evidence all live in repo to meet compliance and knowledge-sharing commitments.
