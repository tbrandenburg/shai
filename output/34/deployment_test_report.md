# Deployment Smoke Test Report — Telegram Router

## Scope
- Exercise `ops/uv_start.sh` with the repo-provided `.env.example` template to ensure configuration guards still execute before the router boots.
- Attempt to reach the `/healthz` probe advertised in the deployment design while documenting the present failure mode when placeholder Telegram credentials prevent a ready response.

## Test Asset
- Script: `tests/smoke/test_deployment.sh` (authored by the test-automator role). It clones `.env.example`, strips conflicting keys, injects smoke overrides (persona map, OTEL header blanking, health host/port, config hash, etc.), and then launches the router through `ops/uv_start.sh` while tailing logs and polling `/healthz`.
- Tooling: `uv 0.9.10`, Python 3.12.3, curl 8.5.0, Bash 5.2. The script enforces `curl` availability and streams router logs to a temporary file for debugging before cleanup.

## Execution Details
1. From `output/34`, ran `../../tests/smoke/test_deployment.sh`. The harness installs `uv` (once) so `ops/uv_start.sh` can resolve project dependencies.
2. The script duplicates `.env.example`, removes the original `ROUTER_*`, `TELEGRAM_PERSONA_MAP`, and `OTEL_EXPORTER_OTLP_HEADERS` entries, and rewrites them with smoke-safe values (`ROUTER_ENV=smoke`, `ROUTER_HEALTH_PORT=18080`, `TELEGRAM_PERSONA_MAP=123456789:operator`, `OTEL_EXPORTER_OTLP_HEADERS=`) to avoid parser errors while keeping the rest of the template intact.
3. `ops/uv_start.sh local --env-file <temp> --log-format json --log-level DEBUG` is spawned in the background; the script polls `http://127.0.0.1:18080/healthz` every 2 s (30 attempts ≈ 60 s) while verifying the router process is still alive.
4. Result: The router never reached a ready state because the stock `.env.example` token is unauthorized. Telegram returned HTTP 401, propagating a `SecurityError`. `/healthz` therefore never responded 200, the smoke harness timed out after 60 s, and it surfaced the tail of the router log for diagnosis.

## Evidence
- Command: ``cd output/34 && ../../tests/smoke/test_deployment.sh``
- Excerpt:
  ```
  Launching router via ops/uv_start.sh
  Router PID: 12314
  Waiting for http://127.0.0.1:18080/healthz
  Timed out waiting for health endpoint. Recent log:
      raise SecurityError(f"telegram 4xx: {exc.code} body={body}") from exc
  SecurityError: telegram 4xx: 401 body={"ok":false,"error_code":401,"description":"Unauthorized"}
  health.tick
  ```
- Exit status: **FAIL** (expected until a Telegram sandbox token or mock transport is available so `/healthz` can flip to ready).

## Follow-ups
- Provide sandbox Telegram credentials or a local fake Telegram transport so the smoke run can complete without external dependencies.
- Implement the documented `/healthz` HTTP responder (none exists in the current codebase) or relax the probe to report degraded status even when Telegram auth fails, enabling automated verification hooks to observe readiness more deterministically.
