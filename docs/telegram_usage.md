# Telegram Router Usage

This guide explains how to provision secrets, bootstrap the uv environment, and run the rebuilt Telegram router described in `docs/telegram_routing_design.md` and `output/34/feature1_architecture.md`.

## Prerequisites
- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) installed and on PATH
- Telegram bot credentials with access to the approved operations chat
- Persona/user ID map agreed with the operations team

## Required Environment Variables
Populate a `.env` file (or export variables in your shell) with the following keys:

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | Bot token from BotFather; must match regex `^\d+:[A-Za-z0-9_-]{35,}$`. |
| `TELEGRAM_CHAT_ID` | yes | Numeric chat ID the router is allowed to serve. Any other chat is rejected. |
| `TELEGRAM_PERSONA_MAP` | yes | JSON or comma list mapping Telegram user IDs to personas (`operator`, `on_call`, `incident_commander`). Example: `{"12345":"operator","67890":"incident_commander"}`. |
| `TELEGRAM_QUEUE_SIZE` | no | Max queued prompts (default 25). |
| `TELEGRAM_POLL_TIMEOUT` | no | Long-poll timeout for `getUpdates` (default 30s). |
| `TELEGRAM_MAX_ATTEMPTS` | no | Automatic retry budget per prompt (default 2). |
| `TELEGRAM_RATE_CAPACITY` / `TELEGRAM_RATE_REFILL_PER_MIN` | no | Token bucket limits for Operators/On-Call (defaults 2 tokens, 6 refills/minute). |
| `TELEGRAM_COMMANDER_CAPACITY` / `TELEGRAM_COMMANDER_REFILL_PER_MIN` | no | Token bucket overrides for Incident Commander (defaults 4 tokens, 12 refills/minute). |
| `TELEGRAM_HEALTH_INTERVAL` | no | Seconds between `health.tick` logs (default 60s). |
| `TELEGRAM_RETRY_CACHE_SIZE` | no | Entries retained for manual `/retry` (default 25). |
| `TELEGRAM_TRANSPORT_MODE` | no | `live` (default) talks to Telegram; `stub` enables the built-in fake transport for offline smoke tests. |
| `TELEGRAM_API_BASE` | no | Optional base URL override when proxying Telegram via gateways; ignored in stub mode. |

Additional Feature 2/adapter variables (e.g., `A2A_BASE_URL`, `A2A_API_KEY`) are loaded by `services/a2a_adapter.py` once implemented; add them to `.env` when the adapter lands.

## Setup & Execution
1. Install dependencies via uv: `uv pip sync`
2. Copy `.env.example` to `.env` (if present) and fill in the required values above.
3. Run the router with uv so dependencies stay deterministic:
   ```bash
   uv run bots/telegram_router.py
   ```
4. Observe structured logs in the terminal. `router.start`, `poll.backoff`, `dispatch.retry`, and `health.tick` events line up with the regenerated architecture docs.
5. Stop the router with `CTRL+C`. The signal handler drains the queue, emits a pause notice, and shuts down gracefully.

## Offline Smoke / Stub Mode
- Use the sandbox credentials already baked into `.env.example` (`TELEGRAM_BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd`, `TELEGRAM_CHAT_ID=123456789`) together with `TELEGRAM_TRANSPORT_MODE=stub` when exercising the router locally or inside CI smoke jobs.
- Stub mode keeps the poll loop, rate limiting, and adapter integration running but routes Telegram traffic through an in-process fake transport, so no external network calls occur.
- Optional: override `TELEGRAM_TRANSPORT_MODE` per environment (`stub` for smoke, `live` everywhere else) rather than editing tokens repeatedly.

## Operational Commands
Operators can manage the router from Telegram once their user IDs appear in `TELEGRAM_PERSONA_MAP`:
- `/status` – shows queue depth, retry cache size, last update ID, and timestamp.
- `/retry <task_id>` – requeues a cached final state by task identifier; responders receive confirmation in-band.
- `/flush` – drains queued prompts and clears the retry cache (incident commander only per policy).

Rate limit breaches trigger explanatory replies with `retry_after` guidance. Queue admits send acceptance notices containing correlation IDs so responders can reference telemetry/adapter traces.

## Persona & Security Notes
- All chat/user IDs are hashed before logging; raw IDs never leave process memory.
- Any chat ID mismatch instantly raises a `security.denied` log entry and the payload is discarded.
- Unknown user IDs (missing from `TELEGRAM_PERSONA_MAP`) receive a denial notice and are logged for auditing.

## Adapter Integration
`bots/telegram_router.py` attempts to import `services/a2a_adapter`. If the adapter has not been rebuilt yet, the router falls back to an `EchoAdapter` that loops prompts back to Telegram so the pipeline can be smoke-tested. When the Feature 2 adapter is delivered, ensure its `build_adapter()` function is importable so prompts are forwarded to `fasta2a_client.py` and downstream systems.

## Troubleshooting
- **No updates received:** verify the bot token is correct and that another worker is not consuming the offset. Use `/status` to check `last_update_id`.
- **Immediate throttling:** confirm the persona mapping is correct—incident commander IDs receive larger buckets.
- **Adapter errors:** look for `a2a.invoke.failed` logs. Until the adapter is rebuilt, the echo fallback will safely return the submitted prompt.
- **Health monitoring:** `health.tick` JSON logs surface queue depth, retry cache usage, and the last update consumed so deployment monitors can alert when the loop stalls.
