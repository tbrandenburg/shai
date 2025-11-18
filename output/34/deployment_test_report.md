# Deployment Smoke Test Report — Telegram Router

## Scope
- Validate that `ops/uv_start.sh` loads repo-provided environment variables and rejects missing config before launching.
- Confirm the standalone health server path returns an `ok` payload when configuration succeeds, proving readiness probes wired in `docs/deployment_design.md` operate end-to-end.

## Test Asset
- Script: `tests/smoke/test_deployment.sh` (new) driven by the test-automator agent, modeled on the deployment runbook.
- Inputs: `.env.example` (cloned into a temporary smoke `.env`) plus the shared ops scripts referenced by the deployment design.
- Tooling stack: `uv 0.9.10`, Python 3.12.3, curl 8.5.0, Bash 5.2. All binaries executed locally inside the repo workspace.

## Execution Details
1. Script copies `.env.example`, pins deterministic smoke overrides (unique TELEGRAM_CHAT_ID, SERVICE_ENV, HEALTHZ_PORT=18080), and runs `ops/uv_start.sh --check-config` to verify TELEGRAM + A2A validation hooks.
2. On success, the script launches `ops/uv_start.sh --health-server` in the background, polling `http://127.0.0.1:18080/healthz` until it returns JSON.
3. Response body is parsed via Python to assert `status == "ok"`; the script kills the server and cleans up temp files afterwards.
4. Command: `tests/smoke/test_deployment.sh` (runtime ≈ 7s, PASS, health server stopped cleanly at PID 11481).

## Evidence
- Config validation: `CONFIG_VALIDATION_OK` surfaced via ops script; failures would have been copied from `/tmp/deployment_smoke_check.log`.
- Health probe: `HEALTHZ_OK` printed with JSON payload `{"status": "ok"}` from the `/healthz` endpoint after one retry, confirming readiness semantics.
- Log artifacts: `/tmp/deployment_smoke_health.log` contains the health server boot logs for triage; automatically removed on next run.

## Follow-ups
- None required. Script can be wired into CI/CD to guard deployment artifacts by invoking the same entrypoints as staging/production supervisors.
