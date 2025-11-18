#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ops/uv_start.sh <environment> [options] [-- <router-args>]
Options:
  --env-file PATH          Path to dotenv file rendered by CI or local env
  --log-level LEVEL        Logging level forwarded to the router (default: INFO)
  --log-format FORMAT      Log format: json or text (default: json)
  --log-forward TARGET     Log drain endpoint (e.g. udp://logs.example:514)
  --metrics-endpoint VAL   Prometheus/StatsD bind string (e.g. :9464)
  --otel                   Enable OpenTelemetry exporters (requires endpoint)
  --otel-endpoint URL      Override OTLP endpoint URL
  --digest DIGEST          OCI image digest recorded for audit trail
  --build-sha SHA          Git SHA injected for observability
  --config-hash HASH       Config manifest hash recorded in telemetry
  --passive                Start in standby mode (ROUTER_ACTIVE=false)
  --skip-sync              Skip the "uv sync" preflight step
  --check-config           Run RouterConfig guard only, then exit
  --uv-arg ARG             Extra flag forwarded to "uv run"
  -h, --help               Show this help message
EOF
}

log() {
  printf '[uv_start] %s\n' "$*" >&2
}

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

ENVIRONMENT="$1"
shift || true
ENV_FILE=""
LOG_LEVEL="INFO"
LOG_FORMAT="json"
LOG_FORWARD=""
METRICS_ENDPOINT=""
ENABLE_OTEL=0
OTEL_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-}"
ROUTER_ACTIVE="true"
DIGEST=""
BUILD_SHA=""
CONFIG_HASH=""
SKIP_SYNC=0
CHECK_ONLY=0
UV_EXTRA_ARGS=()
APP_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="${2^^}"
      shift 2
      ;;
    --log-format)
      LOG_FORMAT="${2,,}"
      shift 2
      ;;
    --log-forward)
      LOG_FORWARD="$2"
      shift 2
      ;;
    --metrics-endpoint)
      METRICS_ENDPOINT="$2"
      shift 2
      ;;
    --otel)
      ENABLE_OTEL=1
      shift
      ;;
    --otel-endpoint)
      ENABLE_OTEL=1
      OTEL_ENDPOINT="$2"
      shift 2
      ;;
    --digest)
      DIGEST="$2"
      shift 2
      ;;
    --build-sha)
      BUILD_SHA="$2"
      shift 2
      ;;
    --config-hash)
      CONFIG_HASH="$2"
      shift 2
      ;;
    --passive)
      ROUTER_ACTIVE="false"
      shift
      ;;
    --skip-sync)
      SKIP_SYNC=1
      shift
      ;;
    --check-config)
      CHECK_ONLY=1
      shift
      ;;
    --uv-arg)
      UV_EXTRA_ARGS+=("$2")
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      APP_ARGS+=("$@")
      break
      ;;
    *)
      APP_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$ENV_FILE" && ! "$ENV_FILE" = /* ]]; then
  ENV_FILE="$REPO_ROOT/$ENV_FILE"
fi
if [[ -n "$ENV_FILE" && ! -f "$ENV_FILE" ]]; then
  log "Env file $ENV_FILE not found"
  exit 1
fi

if [[ "$LOG_FORMAT" != "json" && "$LOG_FORMAT" != "text" ]]; then
  log "Unsupported log format: $LOG_FORMAT"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  log "uv CLI is required but not found. Install from https://astral.sh/uv/."
  exit 1
fi

cd "$REPO_ROOT"

if [[ $SKIP_SYNC -eq 0 ]]; then
  if [[ -f uv.lock ]]; then
    log "Running uv sync --locked"
    uv sync --locked >/dev/null
  elif [[ -f pyproject.toml ]]; then
    log "Running uv sync"
    uv sync >/dev/null
  else
    log "No uv lock or pyproject detected; skipping uv sync"
  fi
fi

mkdir -p /tmp/uv-cache

build_env_vars() {
  ENV_VARS=("ROUTER_ENV=$ENVIRONMENT" "ROUTER_ACTIVE=$ROUTER_ACTIVE" "LOG_LEVEL=$LOG_LEVEL" "LOG_FORMAT=$LOG_FORMAT" "UV_CACHE_DIR=/tmp/uv-cache")
  [[ -n "$LOG_FORWARD" ]] && ENV_VARS+=("LOG_FORWARD_ENDPOINT=$LOG_FORWARD")
  [[ -n "$METRICS_ENDPOINT" ]] && ENV_VARS+=("METRICS_ENDPOINT=$METRICS_ENDPOINT")
  [[ -n "$DIGEST" ]] && ENV_VARS+=("ROUTER_IMAGE_DIGEST=$DIGEST")
  [[ -n "$BUILD_SHA" ]] && ENV_VARS+=("ROUTER_BUILD_SHA=$BUILD_SHA")
  [[ -n "$CONFIG_HASH" ]] && ENV_VARS+=("CONFIG_MANIFEST_HASH=$CONFIG_HASH")
  if [[ $ENABLE_OTEL -eq 1 ]]; then
    ENV_VARS+=("OTEL_ENABLED=1")
    [[ -n "$OTEL_ENDPOINT" ]] && ENV_VARS+=("OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_ENDPOINT")
    ENV_VARS+=("OTEL_SERVICE_NAME=telegram-router")
  fi
}

run_uv() {
  local -a cmd=(uv run)
  if [[ -n "$ENV_FILE" ]]; then
    cmd+=(--env-file "$ENV_FILE")
  fi
  if (( ${#UV_EXTRA_ARGS[@]} )); then
    cmd+=("${UV_EXTRA_ARGS[@]}")
  fi
  cmd+=("$@")
  build_env_vars
  log "Executing: ${cmd[*]}"
  env "${ENV_VARS[@]}" "${cmd[@]}"
}

if [[ $CHECK_ONLY -eq 1 ]]; then
  run_uv python - <<'PY'
import sys
from bots.telegram_router import RouterConfig
try:
    RouterConfig.load()
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"config.invalid: {exc}")
else:
    print("config.valid")
PY
  exit 0
fi

run_uv bots/telegram_router.py "${APP_ARGS[@]}"
