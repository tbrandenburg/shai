# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS runtime

ARG UV_VERSION=0.4.6
ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=container \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    ROUTER_ENV=container \
    ROUTER_ACTIVE=true \
    LOG_FORMAT=json \
    METRICS_ENDPOINT=:9464

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

COPY . .

RUN if [ -f uv.lock ]; then \
      uv sync --locked; \
    elif [ -f pyproject.toml ]; then \
      uv sync; \
    else \
      echo "No uv project metadata found; skipping uv sync"; \
    fi \
    && chmod +x ops/uv_start.sh

EXPOSE 8080 9464
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/healthz || exit 1

USER 65532:65532

ENTRYPOINT ["./ops/uv_start.sh"]
CMD ["production","--env-file","/run/secrets/.env.runtime","--log-format","json","--otel","--metrics-endpoint",":9464"]
