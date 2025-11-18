# Deployment Architecture Plan

## Objective & Scope
Design a uv-focused deployment flow for the Telegram ↔ A2A relay that ensures reproducible process supervision, deterministic secret sourcing, and auditable release promotion across dev, staging, and production. Inputs include `output/34/deployment_requirements.md`, Feature 1/2 specs, and implemented router/adapters.

## Process Supervision Topology
- **Baseline runtime**: All environments package the uv toolchain (`uv`, lockfile, `.python-version`) with the repo. Each launch invokes `uv run bots/telegram_router.py --check-config` prior to entering the polling loop. Structured JSON logs stream to stdout and are captured by the supervisor.
- **Graceful lifecycle**: Supervisors deliver SIGTERM and allow 30s drain time; the router drains inflight polls, flushes logs, and reports final heartbeat before exit. Restart back-off (max 5 attempts/15 min) prevents crash loops.
- **Health probes**: Deployments expose a lightweight `/healthz` (Unix socket or localhost HTTP) served by the router after config validation, plus CI smoke checks that call `uv run bots/telegram_router.py --check-config` and verify Telegram/A2A reachability via mock credentials.

| Environment | Supervision Model | Notes |
| --- | --- | --- |
| Local / Dev | Direct `uv run` or `uvx` launched via make/just target. | Developers rely on `.env` in repo; hot reload disabled to preserve uv lock parity. Logs stay local; optional `entr` watcher for rapid feedback. |
| Staging | System-level supervisor (systemd service or lightweight runit/Procfile) on a CI-managed VM/container. | CI job performs `uv sync`, installs service unit/Procfile, and hands off to supervisor that restarts on failure and publishes structured logs to staging collector. Secrets injected from staging vault at service start. |
| Production | HA pair of containers/pods managed by orchestrator (Kubernetes Deployment, Nomad job, or SupervisorD on active/standby VMs). | Immutable image is built with `uv lock` + exported requirements. Pods mount read-only root FS with tmp scratch; Kubernetes `livenessProbe` hits `/healthz`, `preStop` hook grants 30s drain. Horizontal scaling gated by chat scope rules. |

## Secret Sourcing & Configuration Distribution
1. **Secret catalog enforcement**: `TELEGRAM_BOT_TOKEN`, `A2A_API_KEY`, and other sensitive values live exclusively in the environment secret manager (AWS Secrets Manager, Google Secret Manager, or Vault). Non-secret configuration (`TELEGRAM_POLL_TIMEOUT`, persona tags) is managed via `.env.example` and per-environment manifests tracked in git.
2. **CI templating**: During deploy, CI obtains secrets through workload identity and renders `/run/secrets/.env.runtime` (values masked in logs). Each render records a checksum plus change ticket ID in the deployment audit log.
3. **Runtime delivery**: Supervisors either export env vars before exec or pass `--env-file /run/secrets/.env.runtime` to `uv run`. Files never persist beyond the host TMPFS, and crash dumps scrub secret values via configured log filters.
4. **Configuration parity guard**: Promotion jobs run `config diff` comparing staging vs prod manifests; drift >5% or any missing secret aborts promotion. Approved diffs require linked change tickets and reviewer sign-off stored in CI metadata.
5. **Manifest artifacts**: Every deployment emits a `config-manifest.yaml` summarizing effective non-secret values, secret names (not values), `.env` checksum, uv lock checksum, and build SHA for audit replay.

## Release Promotion Strategy
1. **Source to artifact**: Merges to main trigger CI that runs lint/tests, locks dependencies via `uv lock --frozen`, and builds an OCI image or tarball with the uv toolchain plus bot sources. Artifacts are signed (cosign/slsa provenance) and pushed to the registry.
2. **Staging rollout**: Deployment pipeline pulls the immutable artifact, runs `uv run ... --check-config`, and applies staging config/secret bundles. Systemd or Kubernetes supervisor updates the single staging instance. Smoke tests execute `pytest tests/test_telegram_routing.py` and a Telegram/A2A loopback script to confirm connectivity. Results and log excerpts feed `output/34/deployment_test_report.md`.
3. **Gate checks**: Automated checks verify security scanners (SCA on uv lock, container scans) and ensure observability endpoints are emitting metrics/logs. Manual approval is requested only after config diff passes and all checks are green.
4. **Production promotion**: Upon approval, GitOps-style deployment job promotes the exact artifact digest plus config manifest to production. Kubernetes uses rolling update with maxUnavailable=1; VM/systemd path performs blue/green where standby is brought up, health-checked, then traffic flipped via load balancer or firewall rule.
5. **Post-deploy validation & rollback**: Observability dashboards monitor latency P95, error ratios, and unauthorized chat attempts for 30 minutes. If SLOs breach, rollback is automated: Kubernetes simply redeploys previous ReplicaSet; VM path reverts systemd unit to last known good artifact using recorded build SHA. Rollback also reinstalls the prior config manifest to maintain parity.
6. **Audit trail**: Each promotion logs build SHA, uv lock checksum, config manifest checksum, operator ID, approval ticket, and secret version IDs. Logs reside with deployment notes for compliance review.

## Additional Safeguards
- **Security**: Containers drop `CAP_NET_RAW`, run as non-root, enforce egress allow-lists (Telegram + A2A), and schedule nightly vulnerability scans on the uv lockfile dependencies. CI blocks release on critical CVEs.
- **Observability hooks**: Supervisors inject `env` and `build_sha` labels into all logs/metrics. OTLP exporters are enabled in staging/prod through `OTEL_EXPORTER_OTLP_ENDPOINT` to trace Telegram ↔ A2A spans end-to-end.
- **Documentation as code**: This plan, runbooks, and config manifests are versioned alongside source to satisfy the documentation-as-code principle stated in the DevOps guidelines.
