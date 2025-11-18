# Deployment Design & Runbooks

## Purpose & Scope
Operationalize the regenerated Telegram router plus A2A adapter by translating `output/34/deployment_architecture.md` into concrete runbooks. This document anchors every operator workflow7from local validation to production promotionand binds them to the uv toolchain, `ops/uv_start.sh`, the `Containerfile`, and forthcoming Procfile/Kubernetes manifests.

## Inputs & Required Artifacts
- `uv.lock`, `.python-version`, and repo sources produced by Feature 1 & 2 rebuilds
- `.env.example` (authoritative config + secret catalog) and config manifests rendered per environment
- `ops/uv_start.sh` launcher script (invokes uv with deterministic flags) and Procfile or systemd units
- `Containerfile` (CI artifact) + cosign signature + `uv hash` output
- Deployment evidence log in `output/34/deployment_test_report.md`

## Common Operational Contract
1. **Preflight validation**
   - Run `uv sync --locked`; never vendor ad-hoc dependencies.
   - Execute `uv run bots/telegram_router.py --check-config --env-file <env-file>` to block invalid secrets, persona maps, or queue knobs.
2. **Launch**
   - Prefer `./ops/uv_start.sh <env> --env-file <file>` which handles config guard, logging flags, and health endpoint binding.
   - Supervisors (systemd, Procfile, Kubernetes Deployment) wrap the script and enforce 30s SIGTERM drains.
3. **Health verification**
   - `/healthz` returns 200 only after Telegram + A2A probes succeed; any failure signals `health.tick` with `status=degraded`.
   - Operators must gate traffic or promotions until `curl -fsSL http://127.0.0.1:8080/healthz` (or load balancer URL) passes for 3 consecutive samples.
4. **Observability hookup**
   - stdout/stderr emit JSON logs; forward to the environments drain (dev console, staging log collector, prod SIEM).
   - OTEL exporters toggle via `OTEL_EXPORTER_OTLP_ENDPOINT`; metrics scraped with Prometheus/StatsD sidecar.
5. **Audit trail**
   - Each deployment logs: image digest, `uv.lock` checksum, config manifest hash, operator/approver IDs, and vault version numbers.

## Environment Runbooks

### Local / Dev
1. **Bootstrap**
   ```bash
   uv toolchain install 3.11
   uv sync --locked
   cp .env.example .env # populate with sandbox tokens
   # keep smoke traffic offline
   echo "TELEGRAM_TRANSPORT_MODE=stub" >> .env
   ```
2. **Config guard**
   ```bash
   uv run bots/telegram_router.py --check-config --env-file .env
   ```
3. **Launch**
   ```bash
   ./ops/uv_start.sh local --env-file .env --log-level DEBUG
   ```
   - Script runs `uv run bots/telegram_router.py --env-file .env --emit-metrics stdout`.
4. **Health check**
   ```bash
   curl -fsSL http://127.0.0.1:8080/healthz | jq
   ```
   - Verify `telegram.status` and `a2a.status` fields read `ready`.
   - Keep `TELEGRAM_TRANSPORT_MODE=stub` for smoke/staging dry-runs; flip to `live` only when using production-approved tokens.
5. **Monitoring hooks**
   - Tail logs locally: `jq -r '.event,.status' < logs` or `uv run bots/telegram_router.py --emit-metrics stdout` for queue gauges.
6. **Shutdown**
   - `Ctrl+C` triggers SIGINT; script escalates to SIGTERM if router stalls and waits 30s for drain.

### Staging
1. **CI build**
   ```bash
   uv sync --locked
   uv export --no-hashes --format requirements.txt > dist/requirements.txt
   docker build -f Containerfile -t registry/staging/telegram-router:$GIT_SHA .
   ./scripts/cosign_sign.sh registry/staging/telegram-router:$GIT_SHA
   ```
2. **Secret templating**
   ```bash
   ytt -f deployment/configs/staging -f .env.example > /run/secrets/.env.runtime
   shasum -a 256 /run/secrets/.env.runtime > artifacts/config.sha
   ```
3. **Deploy**
   - Systemd/runit: `sudo systemctl restart telegram-router`
   - Procfile dyno: `heroku release create --procfile Procfile`
   - Manual smoke: `./ops/uv_start.sh staging --env-file /run/secrets/.env.runtime --log-format json`
4. **Health check**
   ```bash
   curl -fsSL https://staging-router.example.com/healthz
   tail -f /var/log/telegram-router.log | jq 'select(.event=="health.tick")'
   ```
   - Block promotion until 30-minute soak shows `latency.round_trip_ms` P95 < 12s and `queue.depth` avg < 5.
5. **Observability**
   - Configure OTEL exporter token via `/run/secrets/otel.token` and set `OTEL_EXPORTER_OTLP_ENDPOINT` env var.
   - Ship logs to staging sink (e.g., `journalctl -u telegram-router -f | logger -n logdrain`).
6. **Evidence capture**
   - Append curl output, `journalctl` excerpt, and config hash to `output/34/deployment_test_report.md`.

### Production
1. **Promotion gates**
   - Verify staging digest signed & scanned: `cosign verify registry/staging/telegram-router:$GIT_SHA`.
   - Run `uv hash --locked` inside build container and compare to stored checksum.
   - Confirm config manifest diff <5% and secrets within rotation policy (Telegram 90d, A2A 180d).
2. **Deployment paths**
   - **Kubernetes GitOps**: update `manifests/router.yaml` digest, then `kubectl apply -k environments/prod`.
   - **VM pair**: pull artifact, replace `/opt/telegram-router` symlink, restart supervisor: `sudo systemctl restart telegram-router@active`.
3. **Launch command (inside container)**
   ```bash
   ./ops/uv_start.sh production --env-file /run/secrets/.env.runtime --otel
   ```
4. **Health & readiness**
   ```bash
   kubectl rollout status deploy/telegram-router -n ops
   kubectl exec deploy/telegram-router -c router -- curl -fsSL http://127.0.0.1:8080/healthz
   ```
   - Standby pod stays passive (`ROUTER_ACTIVE=false`) until failover procedures triggered.
5. **Monitoring hooks**
   - Logs stream to SIEM via Fluent Bit sidecar; confirm ingestion using `kubectl logs deploy/telegram-router -c fluentbit`.
   - Metrics scraped by Prometheus; ensure alert rules for `a2a.failure_total{classification="fatal"}` >3/5m and `router.uptime_seconds` resets.
   - Tracing: verify OTEL exporter handshake by checking `trace.router_prod` dashboard.
6. **Checklist completion**
   - Update deployment logbook with digest, config hash, OTEL token version, and PagerDuty change record.

## Health-Check & Diagnostics Procedures
1. `uv run bots/telegram_router.py --check-config --env-file <env>` (preflight) must finish green; failure reasons logged under `config.guard` event.
2. `/healthz` payload fields:
   - `router.state`: `starting | ready | draining`
   - `telegram.status` / `a2a.status`: `ready`, `degraded`, or `failed`
   - `queue.depth`, `retry_cache.usage`, `persona.rate_window`
3. Diagnostic commands:
   ```bash
   # Inspect rate limiter state
   jq 'select(.event=="rate_limit.hit")' /var/log/telegram-router.log

   # Dump current queue stats
   uv run bots/telegram_router.py --inspect-queue --env-file <env>
   ```
4. Health incidents escalate when `/healthz` fails twice or `router.uptime_seconds` resets unexpectedly; responders capture logs + metrics before restart.

## Monitoring & Alerting Hooks
- **Metrics collectors**: configure `METRICS_ENDPOINT=:9464` so Prometheus scrapes `latency.round_trip_ms`, `queue.depth`, `a2a.failure_total`, `router.uptime_seconds`, `rate_limit.hit`.
- **Dashboards**: `telegram_router_latency`, `telegram_router_queue`, `a2a_failures`, `router_rollouts` (annotate deploys with git SHA + manifest hash).
- **Alert rules**
  - Warn: `rate_limit.hit` >10/persona/12h
  - Page: `a2a.failure_total{classification="fatal"}` >3 within 5m
  - Page: `queue.depth` >20 for >120s or `router.uptime_seconds` resets >1/day without change record
- **Telemetry fields**: ensure every log adds `env`, `build_sha`, `persona_tag`, `chat_id_hash`, and `config_manifest_hash` for traceability.

## Log Aggregation Steps
1. **Local**: optional `uv run bots/telegram_router.py --emit-metrics stdout`; logs stay on console, but developers may push to local Loki via `./ops/uv_start.sh local --log-forward tcp://localhost:1514`.
2. **Staging**: `ops/uv_start.sh` supports `--log-forward udp://logs.staging.example:514`; configure token via `LOG_DRAIN_TOKEN` secret (90-day rotation). Verify ingestion with `curl -H "Authorization: Bearer $LOG_DRAIN_TOKEN" https://logs.staging.example/api/v1/status`.
3. **Production**: Fluent Bit sidecar ships to SIEM with TLS + token from vault. Validate using `kubectl logs deploy/telegram-router -c fluentbit | grep delivered`. Retain logs 90 days, enforce RBAC + break-glass approvals for queries.

## Rollback & Recovery
1. **Config rollback**
   - Revert manifest/digest pair in Git, regenerate `.env.runtime`, and redeploy via GitOps or supervisor restart.
   - Document rollback reason + incident ID in deployment log.
2. **Artifact rollback**
   ```bash
   kubectl rollout undo deploy/telegram-router -n ops
   # or
   ./ops/uv_start.sh production --env-file /run/secrets/.env.runtime --digest <previous>
   ```
3. **Secret rotation incident**
   - Rotate secret, regenerate manifest, rerun `uv run ... --check-config`, redeploy, and attach rotation ticket.
4. **Disaster recovery**
   - Pull last signed OCI digest + config manifest from registry
   - Restore environment: `docker pull registry/prod/telegram-router:<digest>`; replay manifest to vault; launch via runbook above within 30 minutes.
5. **Post-incident review**
   - Add telemetry snapshots (logs/metrics) and timeline to `output/34/deployment_test_report.md`
   - Update this document if gaps identified.

## Appendices
- **Reference scripts**: `ops/uv_start.sh`, `scripts/pipeline_task_machine.sh` (invocation context), `scripts/pipeline_rfq*.sh` for CI patterns.
- **Future assets**: `Containerfile`, `Procfile`, `ops/uv_start.sh`, and test harness under `tests/smoke/test_deployment.sh` will consume this runbook verbatim once authored.
