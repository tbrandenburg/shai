# Deployment Smoke Test Report — Telegram Router

## Scope
- Validate that `ops/uv_start.sh` loads repo-provided environment variables and rejects missing config before launching.
- Confirm the standalone health server path returns an `ok` payload when configuration succeeds, proving readiness probes wired in `docs/deployment_design.md` operate end-to-end.

## Test Asset
- Script: `tests/smoke/test_deployment.sh` (new) driven by the test-automator agent, modeled on the deployment runbook.
- Inputs: `.env.example` (cloned into a temporary smoke `.env`) plus the shared ops scripts referenced by the deployment design.
- Tooling stack: `uv 0.9.10`, Python 3.12.3, curl 8.5.0, Bash 5.2. All binaries executed locally inside the repo workspace.

## Execution Details
1. The smoke harness duplicates `.env.example`, appends deterministic overrides (SERVICE_ENV=smoke, CONFIG_MANIFEST_ID=smoke-test, HEALTHZ_PORT=18080, TELEGRAM_ACTIVE_POLLER=false, A2A_LOOPBACK=true, and a regex-compliant TELEGRAM token/chat ID) so no production secrets are touched.
2. `ops/uv_start.sh --env-file <temp> --skip-lock --skip-compile check` executes first; the loader logs `sha256=55d154fb983f1ca86cd5e5a56605892144c27b29c7a70a3fa6d56f089282d5fc` for traceability and emits `CONFIG_VALIDATION_OK`, demonstrating the config gate passes even when the `uv` binary is absent (Python fallback kicks in automatically).
3. The script backgrounds `ops/uv_start.sh --env-file <temp> --skip-lock --skip-compile health-server`, captures `HEALTH_SERVER_PID=16856`, and polls `http://127.0.0.1:18080/healthz` until the JSON payload reports `status == "ok"`.
4. Command (from `output/34`): `../../tests/smoke/test_deployment.sh` (≈4s). Health logs stream into `/tmp/telegram_router_smoke_health.log` during execution and are deleted unless `KEEP_HEALTH_LOG=1` is set.

## Evidence
- `CONFIG_VALIDATION_OK` (stdout) — proves the ops gate accepted the synthetic env file; the full trace lives in `/tmp/telegram_router_smoke_check.log` while the run is active.
- `HEALTH_SERVER_PID=16856` — background server tracked for cleanup, matching the PID recorded in the console output.
- `HEALTHZ_OK {"status": "ok", "service_env": "smoke", "config_manifest_id": "smoke-test", "env_sha256": "55d154fb983f1ca86cd5e5a56605892144c27b29c7a70a3fa6d56f089282d5fc", "timestamp": "2025-11-18T16:25:20Z"}` — confirms the readiness probe contract returns JSON once config validation succeeds.

## Follow-ups
- None required. Script can be wired into CI/CD to guard deployment artifacts by invoking the same entrypoints as staging/production supervisors.
