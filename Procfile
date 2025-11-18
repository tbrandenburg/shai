release: ./ops/uv_start.sh staging --env-file /run/secrets/.env.runtime --check-config
worker: ./ops/uv_start.sh staging --env-file /run/secrets/.env.runtime --log-format json --metrics-endpoint :9464 --otel --log-forward udp://logs.staging.example:514
