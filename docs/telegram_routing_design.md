# Telegram Routing Design

## 1. Scope & Objectives
- Rebuild the Telegram router described in `output/34/feature1_requirements.md` and `output/34/feature1_architecture.md` with deterministic implementation guidance.
- Provide module-level responsibilities, dependency injection seams, and control flows for the uv-managed app so backend work proceeds without ambiguity.
- Concretely define validation helpers, dispatch layers, logging expectations, and error handling logic aligned with personas (Operator, On-Call Responder, Incident Commander).

## 2. Runtime Summary
- Entrypoint executes via `uv run bots/telegram_router.py`, ensuring reproducible environments and dependency syncing via `uv pip sync`.
- `bots/telegram_router.py` configures an `asyncio` event loop hosting: Telegram polling, ingestion/validation, queue + rate limiter, single-flight dispatcher, reply sender, command processor, and `/healthz` task.
- The router enforces one in-flight task, queue depth 25, and per-user token buckets (6 prompts/min; Incident Commander priority) with exponential backoff instructions after rate hits.

## 3. Module Boundaries
### 3.1 bots/telegram_router.py (entrypoint & DI container)
- Loads `RouterConfig` (env vars + persona maps + polling parameters) using `pydantic` validation helpers.
- Establishes structured logger (JSON), OTEL tracer exporter, and metrics recorder.
- Constructs dependency bundle:
  - `TelegramClient` wrapper (aiohttp session + request signing) seeded by validated `TELEGRAM_BOT_TOKEN`.
  - `RouterQueue` (asyncio.Queue) with instrumentation hooks to publish queue depth metrics.
  - `PersonaRateLimiter` (token bucket map) keyed by persona+user_hash with overrides for Incident Commander.
  - `CommandDispatcher` referencing persona command registry and audit logger.
  - `A2AForwarder` (adapter shim) implementing `RouterAdapter` protocol (see §5).
- Registers background tasks via `asyncio.create_task`: `poll_updates`, `ingest_and_enqueue`, `single_flight_dispatcher`, `reply_dispatcher`, `command_listener`, `health_tick`, and graceful shutdown watchers.

### 3.2 bots/validation.py (validation helpers)
- `validate_env(config)` – regex check token (`^\d+:[A-Za-z0-9_-]{35,}$`), enforce chat ID int64 bounds, fail-fast on missing persona map or env mismatch.
- `sanitize_message(message: str) -> SanitizedMessage` – trim, collapse whitespace, strip HTML/markdown control characters, enforce 2,000-char limit, reject media payloads.
- `map_persona(user_id: int) -> Persona` – resolves Operator/On-Call/Incident Commander via config map, default denies unknown IDs, logs hashed user.
- `hash_identifier(raw_id: str|int) -> str` – sha256 utility reused for chat/user logging and metrics.
- `validate_command(command_text: str)` – ensures `/retry <correlation>` syntax, `/throttle` arguments, etc., surfacing descriptive Telegram responses when malformed.

### 3.3 bots/dispatcher.py (message + command routing)
- Exposes `RouterDispatcher` class with two primary coroutines:
  - `handle_prompt(router_msg: RouterMessage)` – rate limit, enqueue, send busy notice with queue position, emit `router.prompt.accepted` metric.
  - `handle_command(command_msg: CommandMessage)` – call `CommandRegistry` (below) and route response to `reply_dispatcher` without occupying single-flight semaphore unless `/retry` requires re-dispatch.
- Maintains `asyncio.Semaphore(max_inflight=1)` to serialize A2A calls; `DispatchContext` attaches correlation IDs, persona tags, and timestamps for telemetry.

### 3.4 bots/commands.py (command registry & audit trail)
- Defines `CommandRegistry` mapping strings to handler coroutines (`/status`, `/flush`, `/retry`, `/throttle`, `/resume`).
- `/status` aggregates queue depth, hashed chat ID, token age bucket, outstanding final states, and exposes token rotation age.
- `/retry <task_id>` fetches payload from `ManualRetryCache` (see §4.2) and requeues if eligible.
- Each handler logs `{command, persona, user_hash, timestamp, effect}` to structured logs + metrics counter `telegram.command.invoke`.

### 3.5 bots/rate_limiter.py
- Implements reusable token bucket with per-user/per-persona configuration (`capacity=2`, `refill_rate=6/min`).
- Provides `RateLimitDecision` result object (allowed, retry_after seconds, violation_count) consumed by dispatcher for response messaging.

### 3.6 bots/metrics.py
- Wraps OpenTelemetry or Prometheus client with helpers to record counters (`messages.processed`, `final_state.*`), histograms (`round_trip_ms`, `queue_wait_ms`), and gauges (`queue.depth`, `token.age_days`).
- Adds `emit_security_denied`, `emit_retry`, `emit_rate_hit` helper functions for consistent labeling.

### 3.7 bots/retry_buffer.py
- Maintains bounded deque (25 entries) storing `RetryRecord` {correlation_id, telegram_message_id, sanitized_payload, last_final_state, retry_count}.
- Supports TTL eviction and retrieval by command `/retry <task_id>` or correlation ID; ensures hashed IDs only.

### 3.8 services/a2a_adapter.py (glue layer, forward reference)
- Adapter exposes async `invoke(request: A2ARequest) -> A2AResponse` executed via `asyncio.to_thread` calling `fasta2a_client.py` to preserve compatibility until Feature 2 replaces it.
- Handles translation of final states, distinguishing `RetryableA2AError` vs terminal errors, and surfaces diagnostics + `retry_after` hints for backoff controller.

## 4. Core Data Structures
### 4.1 RouterMessage
```python
@dataclass
class RouterMessage:
    update_id: int
    chat_hash: str
    user_hash: str
    persona: Persona
    telegram_message_id: int
    payload: str
    timestamp: datetime
    correlation_id: str
```

### 4.2 ManualRetryCache
- `add(record: RetryRecord)` called once per final state completion, storing sanitized payload + final diagnostics.
- `get(task_id: str) -> RetryRecord | None` for `/retry`.
- Evicts records older than 25 entries or >24h to honor memory cap.

### 4.3 A2ARequest / Response
```python
class RouterAdapter(Protocol):
    async def invoke(self, request: A2ARequest) -> A2AResponse: ...

@dataclass
class A2ARequest:
    prompt: str
    persona: str
    correlation_id: str
    telegram_user_hash: str
    queue_entered_at: datetime
    attempt: int

@dataclass
class A2AResponse:
    final_state: Literal['completed','failed','canceled','rejected']
    text: str
    task_id: str
    diagnostics: dict[str, Any]
    retryable: bool
    latency_ms: int
```

## 5. Dependency Injection & Configuration
- `RouterConfig` dataclass sourced from env (token, chat ID, rate limits, queue size, telemetry toggles). Use pydantic to validate types, default queue size 25, poll timeout 30s.
- `build_dependencies(config)` constructs Telegram/A2A clients. Dependencies are injected into tasks via closure variables or explicit `Dependencies` dataclass to support testing.
- Provide seam for swapping `services/a2a_adapter.py` with mock during tests (Feature 2 shares interface).
- Telemetry exporters (OTEL endpoint, metrics labels) also injected for determinism and to avoid hidden globals.

## 6. Control Flow Details
1. **Startup (`main()`):**
   - Load `.env`/environment, run `validate_env`. Abort with redacted error if token/chat invalid.
   - Instantiate dependencies and register signal handlers for SIGINT/SIGTERM to trigger `graceful_shutdown()`.
   - Kick off asynchronous tasks and await `asyncio.Event` signifying fatal failure.
2. **Polling (`poll_updates_task`):**
   - Call Telegram `getUpdates` with `timeout=30`, `allowed_updates=['message']`, and track `offset`. On success push raw updates into `asyncio.Queue` `incoming_updates`.
   - On HTTP 5xx apply capped exponential backoff (1s, 3s, 7s, 15s, 30s, 60s) and emit `polling.backoff` metric.
3. **Ingestion & Validation:**
   - Convert updates to `RouterMessage`, verifying chat ID equals configured ID. Unauthorized traffic triggers `SECURITY_DENIED` log, `emit_security_denied`, and optional denial reply.
   - Commands (payload starts with `/`) routed to command queue; prompts forwarded to rate limiter.
4. **Rate limiting & Queueing:**
   - `PersonaRateLimiter` returns allow/deny. Denied prompts respond with throttle notice containing `retry_after` and violation count, referencing requirements guardrails.
   - Allowed prompts append to `RouterQueue`; when queue >0 respond with busy notice containing queue position + correlation ID to maintain transparency.
5. **Single Flight Dispatch:**
   - `single_flight_dispatcher` waits on queue, acquires semaphore, builds `A2ARequest`, and `await adapter.invoke`. Execution time recorded for acceptance metrics.
6. **Final-State Handling:**
   - On success, send formatted Telegram reply (MarkdownV2 safe) including final state, task ID, correlation ID.
   - On retryable failure, increment attempt count (max 2), requeue with exponential backoff using `asyncio.sleep` before re-enqueue.
   - Always insert record into `ManualRetryCache` with final diagnostics.
7. **Command Handling:**
   - `/status` composes summary (queue depth, last offset, hashed chat ID, token age bucket, final-state counts) and dispatches via `reply_dispatcher`.
   - `/retry` fetches record. If missing or TTL expired responds with instructive error referencing acceptance metrics.
   - `/flush` drains queue + cache, logging actions.
8. **Health Tick:**
   - Every 60s revalidate env, compute token age, ensure chat ID still matches, emit `/healthz` output for deployment monitors. If validation fails, set `circuit_breaker.set()` causing dispatcher to reject prompts until resolved.
9. **Graceful Shutdown:**
   - On signal, stop polling, set `shutdown_event`, drain queue, notify chat "bot paused" with correlation ID, flush logs, close aiohttp session.

## 7. Logging, Metrics, Observability
- Structured JSON logs with keys: `timestamp`, `level`, `correlation_id`, `chat_hash`, `user_hash`, `persona`, `event`, `queue_depth`, `latency_ms`, `final_state`, `command`, `retry_count`, `token_age_days`.
- Metrics:
  - Counters: `telegram.messages.processed`, `telegram.security.denied`, `telegram.command.invoke`, `telegram.rate_limit.hit`, `telegram.final_state.completed|failed|canceled|rejected`.
  - Histograms: `telegram.round_trip.latency_ms`, `telegram.queue.wait_ms`, `a2a.invoke.latency_ms`.
  - Gauges: `telegram.queue.depth`, `telegram.token.age_days`, `telegram.rate_limit.remaining`.
- Tracing: Each major coroutine starts OTEL span with correlation ID attribute to satisfy observability requirements.

## 8. Error Handling & Backoff
- Distinguish error classes:
  - `ConfigError` (invalid env or chat mismatch) – fatal; triggers shutdown.
  - `SecurityError` (unauthorized chat/user) – respond, log, continue.
  - `RateLimitError` – respond with throttle message + `retry_after` guidance.
  - `TransientTelegramError` (5xx/timeout) – exponential backoff + jitter; pause after 3 consecutive to protect SLAs.
  - `A2ATransientError` – single retry respecting `retry_after` or default 2s; after failure, send actionable message referencing diagnostics.
  - `A2ATerminalError` – send failure summary, keep payload in cache for manual `/retry` with sanitized context.
- All errors propagate correlation IDs and hashed IDs for auditing; no secrets logged.

## 9. Configuration & Secrets Handling
- `.env.example` documents required variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `A2A_BASE_URL`, `A2A_API_KEY?`, `UV_LOG_LEVEL`.
- Startup validation includes token regex, chat ID 64-bit bounds, persona map presence, and hashed chat ID log for `/status` verification.
- Secrets never written to disk; stored only in memory. Logging of IDs uses sha256 hash.
- `/status` includes token age bucket ( <30d / 30-60d / 60-90d / >90d ) and warns when >75d.

## 10. Testing Guidance
- Unit tests for validation helpers (token regex, chat gating, persona mapping, sanitization).
- Integration tests using mocked Telegram HTTP responses + fake adapter to verify queueing, rate limits, and final-state replies.
- Command handler tests verifying `/status` output fields, `/retry` flows, and manual queue flush.
- Observability tests ensuring metrics/log schema includes required keys.
- Harness to simulate 6 prompts/min per user verifying throttle/backoff messages.

## 11. Implementation Checklist
1. Implement `RouterConfig` and validation helpers.
2. Build Telegram client wrapper + polling task with offset persistence.
3. Implement rate limiter + queue instrumentation.
4. Create dispatcher + command registry + retry buffer.
5. Integrate `services/a2a_adapter.py` that calls `fasta2a_client.py` with proper schema + final state translation.
6. Wire logging/metrics/tracing and `/healthz` reporting.
7. Provide CLI/README snippet (see future `docs/telegram_usage.md`) demonstrating env setup and `uv run` invocation.

This design specifies every module boundary, contract, and operational control so implementation can proceed to rebuild the uv-based Telegram router with the rigor expected in the requirements and architecture artifacts.
