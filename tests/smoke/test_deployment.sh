#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
ENV_TEMPLATE="$REPO_ROOT/.env.example"
ENV_FILE=$(mktemp)
RUN_LOG=$(mktemp)
HEALTH_URL="http://127.0.0.1:18080/healthz"
ROUTER_PID=""
LAST_HEALTH_PAYLOAD=""

require_binary() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Missing required binary: $bin" >&2
    exit 1
  fi
}

stop_router() {
  if [[ -n "$ROUTER_PID" ]] && kill -0 "$ROUTER_PID" >/dev/null 2>&1; then
    echo "Stopping router (PID $ROUTER_PID)" >&2
    kill "$ROUTER_PID" >/dev/null 2>&1 || true
    wait "$ROUTER_PID" >/dev/null 2>&1 || true
  fi
  ROUTER_PID=""
}

cleanup() {
  local exit_code="$1"
  trap - EXIT
  stop_router
  rm -f "$ENV_FILE" "$RUN_LOG"
  exit "$exit_code"
}
trap 'cleanup $?' EXIT

if [[ ! -f "$ENV_TEMPLATE" ]]; then
  echo "Missing env template at $ENV_TEMPLATE" >&2
  exit 1
fi

require_binary curl

cp "$ENV_TEMPLATE" "$ENV_FILE"
python - <<'PY' "$ENV_FILE"
import sys
from pathlib import Path

path = Path(sys.argv[1])
override_keys = {
    "ROUTER_ENV",
    "ROUTER_HEALTH_HOST",
    "ROUTER_HEALTH_PORT",
    "LOG_LEVEL",
    "CONFIG_MANIFEST_HASH",
    "ROUTER_BUILD_SHA",
    "A2A_API_KEY",
    "TELEGRAM_PERSONA_MAP",
    "OTEL_EXPORTER_OTLP_HEADERS",
}
lines = path.read_text(encoding="utf-8").splitlines()
with path.open("w", encoding="utf-8") as fh:
    for line in lines:
        stripped = line.strip()
        if not stripped:
            fh.write("\n")
            continue
        if stripped.startswith("#"):
            fh.write(line + "\n")
            continue
        key, _, _ = line.partition("=")
        if key in override_keys:
            continue
        fh.write(line + "\n")
PY

cat >>"$ENV_FILE" <<'EOF'
ROUTER_ENV=smoke
ROUTER_HEALTH_HOST=127.0.0.1
ROUTER_HEALTH_PORT=18080
LOG_LEVEL=DEBUG
CONFIG_MANIFEST_HASH=smoke-test
ROUTER_BUILD_SHA=smoke-run
A2A_API_KEY=smoke-test-key
TELEGRAM_PERSONA_MAP=123456789:operator
TELEGRAM_TRANSPORT_MODE=stub
OTEL_EXPORTER_OTLP_HEADERS=
EOF

echo "Launching router via ops/uv_start.sh"
"${REPO_ROOT}/ops/uv_start.sh" local --env-file "$ENV_FILE" --log-format json --log-level DEBUG >"$RUN_LOG" 2>&1 &
ROUTER_PID=$!
echo "Router PID: $ROUTER_PID"

echo "Waiting for $HEALTH_URL"
for attempt in $(seq 1 30); do
  if ! kill -0 "$ROUTER_PID" >/dev/null 2>&1; then
    echo "Router exited before health check succeeded. Recent log:" >&2
    tail -20 "$RUN_LOG" >&2 || true
    exit 1
  fi
  if HEALTH_PAYLOAD=$(curl -fsS "$HEALTH_URL" 2>/dev/null); then
    LAST_HEALTH_PAYLOAD="$HEALTH_PAYLOAD"
    echo "Healthz success on attempt $attempt: $HEALTH_PAYLOAD"
    break
  fi
  sleep 2
  if [[ "$attempt" -eq 30 ]]; then
    echo "Timed out waiting for health endpoint. Recent log:" >&2
    tail -20 "$RUN_LOG" >&2 || true
    exit 1
  fi
done

stop_router

echo "Smoke deployment test passed"
echo "Health payload: $LAST_HEALTH_PAYLOAD"
