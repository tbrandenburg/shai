"""Telegram router entrypoint rebuilt per docs/telegram_routing_design.md.

This module orchestrates long polling, validation, rate limiting, queueing,
single-flight dispatching to the A2A adapter, and structured replies back to
Telegram chats. It intentionally keeps all orchestration logic in a single
file so downstream adapters/tests can import the Router surface easily until
additional modules are reintroduced.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import os
import re
import signal
import uuid
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional, Protocol, cast


TELEGRAM_TOKEN_REGEX = re.compile(r"^\d+:[A-Za-z0-9_-]{35,}$")
LOGGER = logging.getLogger("telegram.router")


class ConfigError(RuntimeError):
    """Raised when router configuration or startup validation fails."""


class SecurityError(RuntimeError):
    """Raised when an unauthorized user or chat attempts to interact."""


class TransientTelegramError(RuntimeError):
    """Raised when Telegram API returns retryable errors."""


class RouterAdapter(Protocol):
    """Protocol for adapter implementations (services/a2a_adapter.py)."""

    async def invoke(self, request: "A2ARequest") -> "A2AResponse": ...


@dataclass(slots=True)
class A2ARequest:
    prompt: str
    persona: str
    correlation_id: str
    telegram_user_hash: str
    queue_entered_at: datetime
    attempt: int
    chat_hash: str | None = None
    telegram_message_id: int | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class A2AResponse:
    final_state: Literal["completed", "failed", "canceled", "rejected"]
    text: str
    task_id: str
    diagnostics: Dict[str, Any]
    retryable: bool
    latency_ms: int


@dataclass(slots=True)
class RouterMessage:
    update_id: int
    persona: str
    payload: str
    telegram_message_id: int
    chat_hash: str
    user_hash: str
    correlation_id: str
    attempt: int = 1
    queue_entered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(slots=True)
class CommandMessage:
    update_id: int
    command: str
    args: list[str]
    persona: str
    telegram_message_id: int
    chat_hash: str
    user_hash: str
    timestamp: datetime


@dataclass(slots=True)
class RetryRecord:
    task_id: str
    payload: str
    persona: str
    chat_hash: str
    user_hash: str
    last_final_state: str
    diagnostics: Dict[str, Any]
    stored_at: datetime


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after: float = 0.0
    violation_count: int = 0


@dataclass(slots=True)
class ComponentHealth:
    status: Literal["starting", "ready", "degraded", "failed"] = "starting"
    last_success: datetime | None = None
    last_error: str | None = None

    def mark_success(self) -> None:
        self.status = "ready"
        self.last_success = datetime.now(timezone.utc)
        self.last_error = None

    def mark_failure(self, error: str) -> None:
        self.status = "failed"
        self.last_error = (error or "")[:400]

    def resolved_status(self, now: datetime, stale_after: int) -> str:
        if self.status == "failed":
            return "failed"
        if self.last_success:
            if (now - self.last_success).total_seconds() > stale_after:
                return "degraded"
            return "ready"
        return self.status

    def payload(self, now: datetime, stale_after: int) -> Dict[str, Any]:
        return {
            "status": self.resolved_status(now, stale_after),
            "last_success": self.last_success.isoformat()
            if self.last_success
            else None,
            "last_error": self.last_error,
        }


class ManualRetryCache:
    """Bounded cache for storing final-state information."""

    def __init__(self, max_entries: int = 25) -> None:
        self._records: deque[RetryRecord] = deque(maxlen=max_entries)
        self._max_entries = max_entries

    def add(self, record: RetryRecord) -> None:
        self._records.append(record)

    def get(self, task_id: str) -> Optional[RetryRecord]:
        for record in self._records:
            if record.task_id == task_id:
                return record
        return None

    def clear(self) -> None:
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)

    @property
    def capacity(self) -> int:
        return self._max_entries


class PersonaRateLimiter:
    """Token bucket per (persona,user) tuple."""

    def __init__(
        self,
        default_capacity: int,
        default_refill_per_min: int,
        commander_capacity: int,
        commander_refill_per_min: int,
    ) -> None:
        self._default_capacity = default_capacity
        self._default_refill = default_refill_per_min / 60
        self._commander_capacity = commander_capacity
        self._commander_refill = commander_refill_per_min / 60
        self._buckets: Dict[str, Dict[str, float]] = {}

    def check(
        self, persona: str, user_hash: str, now: Optional[datetime] = None
    ) -> RateLimitDecision:
        now = now or datetime.now(timezone.utc)
        key = f"{persona}:{user_hash}"
        bucket = self._buckets.setdefault(
            key,
            {
                "tokens": float(self._capacity(persona)),
                "ts": now.timestamp(),
                "violations": 0,
            },
        )
        elapsed = max(0.0, now.timestamp() - bucket["ts"])
        refill_rate = self._refill(persona)
        bucket["tokens"] = min(
            self._capacity(persona), bucket["tokens"] + elapsed * refill_rate
        )
        bucket["ts"] = now.timestamp()
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            bucket["violations"] = 0
            return RateLimitDecision(True)
        bucket["violations"] = int(bucket["violations"]) + 1
        retry_after = (1 - bucket["tokens"]) / (refill_rate or 0.0001)
        return RateLimitDecision(
            False,
            retry_after=retry_after,
            violation_count=int(bucket["violations"]),
        )

    def _capacity(self, persona: str) -> int:
        return (
            self._commander_capacity
            if persona.lower() == "incident_commander"
            else self._default_capacity
        )

    def _refill(self, persona: str) -> float:
        return (
            self._commander_refill
            if persona.lower() == "incident_commander"
            else self._default_refill
        )

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tracked": len(self._buckets),
            "default_capacity": self._default_capacity,
            "default_refill_per_min": int(self._default_refill * 60),
            "commander_capacity": self._commander_capacity,
            "commander_refill_per_min": int(self._commander_refill * 60),
        }


@dataclass(slots=True)
class RouterConfig:
    telegram_bot_token: str
    telegram_chat_id: int
    persona_map: Dict[int, str]
    transport_mode: Literal["live", "stub"] = "live"
    telegram_api_base: str = "https://api.telegram.org"
    queue_size: int = 25
    poll_timeout: int = 30
    retry_attempts: int = 2
    rate_capacity: int = 2
    rate_refill_per_min: int = 6
    commander_capacity: int = 4
    commander_refill_per_min: int = 12
    health_interval: int = 60
    retry_cache_size: int = 25
    health_host: str = "0.0.0.0"
    health_port: int = 8080
    health_path: str = "/healthz"

    def __post_init__(self) -> None:
        if self.transport_mode not in {"live", "stub"}:
            raise ConfigError("TELEGRAM_TRANSPORT_MODE must be 'live' or 'stub'")
        if self.transport_mode != "stub" and not TELEGRAM_TOKEN_REGEX.match(
            self.telegram_bot_token
        ):
            raise ConfigError("TELEGRAM_BOT_TOKEN failed validation")
        if self.queue_size <= 0:
            raise ConfigError("queue_size must be positive")
        if self.poll_timeout < 5 or self.poll_timeout > 60:
            raise ConfigError("poll_timeout must be between 5 and 60")
        if self.retry_attempts < 1:
            raise ConfigError("retry_attempts must be >= 1")
        if not self.persona_map:
            raise ConfigError("TELEGRAM_PERSONA_MAP required")
        if self.health_port <= 0 or self.health_port > 65535:
            raise ConfigError("ROUTER_HEALTH_PORT must be between 1 and 65535")
        if not self.health_path.startswith("/"):
            raise ConfigError("ROUTER_HEALTH_PATH must start with '/'")

    @classmethod
    def load(cls) -> "RouterConfig":
        persona_map_raw = os.getenv("TELEGRAM_PERSONA_MAP", "{}")
        persona_map = cls._parse_persona_map(persona_map_raw)
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise ConfigError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
        transport_mode = (
            (os.getenv("TELEGRAM_TRANSPORT_MODE", "live") or "live").strip().lower()
        )
        if transport_mode in {"live", "stub"}:
            mode = cast(Literal["live", "stub"], transport_mode)
        else:
            mode = "live"
        api_base_raw = (
            os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
            or "https://api.telegram.org"
        )
        api_base = api_base_raw.strip().rstrip("/") or "https://api.telegram.org"
        return cls(
            telegram_bot_token=token,
            telegram_chat_id=int(chat_id),
            persona_map=persona_map,
            transport_mode=mode,
            telegram_api_base=api_base,
            queue_size=int(os.getenv("TELEGRAM_QUEUE_SIZE", 25)),
            poll_timeout=int(os.getenv("TELEGRAM_POLL_TIMEOUT", 30)),
            retry_attempts=int(os.getenv("TELEGRAM_MAX_ATTEMPTS", 2)),
            rate_capacity=int(os.getenv("TELEGRAM_RATE_CAPACITY", 2)),
            rate_refill_per_min=int(os.getenv("TELEGRAM_RATE_REFILL_PER_MIN", 6)),
            commander_capacity=int(os.getenv("TELEGRAM_COMMANDER_CAPACITY", 4)),
            commander_refill_per_min=int(
                os.getenv("TELEGRAM_COMMANDER_REFILL_PER_MIN", 12)
            ),
            health_interval=int(os.getenv("TELEGRAM_HEALTH_INTERVAL", 60)),
            retry_cache_size=int(os.getenv("TELEGRAM_RETRY_CACHE_SIZE", 25)),
            health_host=os.getenv("ROUTER_HEALTH_HOST", "0.0.0.0") or "0.0.0.0",
            health_port=int(os.getenv("ROUTER_HEALTH_PORT", 8080)),
            health_path=cls._normalize_health_path(
                os.getenv("ROUTER_HEALTH_PATH", "/healthz")
            ),
        )

    @staticmethod
    def _parse_persona_map(raw: str) -> Dict[int, str]:
        if not raw:
            return {}
        raw = raw.strip()
        try:
            parsed = json.loads(raw)
            return {int(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            mapping: Dict[int, str] = {}
            for chunk in raw.split(","):
                if not chunk:
                    continue
                user, _, persona = chunk.partition(":")
                if user and persona:
                    mapping[int(user.strip())] = persona.strip()
            return mapping

    @staticmethod
    def _normalize_health_path(raw: str | None) -> str:
        path = (raw or "/healthz").strip() or "/healthz"
        if not path.startswith("/"):
            path = f"/{path}"
        return path


class TelegramClient:
    """Small wrapper above Telegram Bot HTTP API built on urllib."""

    def __init__(
        self, token: str, *, api_base: str = "https://api.telegram.org"
    ) -> None:
        base = api_base.rstrip("/")
        self._base_url = f"{base}/bot{token}"

    async def close(self) -> None:  # pragma: no cover - nothing to close for urllib
        return None

    async def get_updates(
        self, *, offset: Optional[int], timeout: int
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._sync_get_updates, offset, timeout)

    async def send_message(
        self, *, chat_id: int, text: str, parse_mode: str = "MarkdownV2"
    ) -> None:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        await asyncio.to_thread(self._sync_post_json, "/sendMessage", payload)

    def _sync_get_updates(
        self, offset: Optional[int], timeout: int
    ) -> list[dict[str, Any]]:
        params = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            params["offset"] = offset
        query = urllib.parse.urlencode(params)
        url = f"{self._base_url}/getUpdates?{query}"
        request = urllib.request.Request(url, method="GET")
        data = self._execute_json_request(request, timeout + 5)
        if not data.get("ok"):
            raise TransientTelegramError(str(data))
        return data.get("result", [])

    def _sync_post_json(self, path: str, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        response = self._execute_json_request(request, 30)
        if not response.get("ok"):
            raise TransientTelegramError(str(response))

    def _execute_json_request(
        self, request: urllib.request.Request, timeout: int
    ) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=max(timeout, 10)) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            self._handle_http_error(exc)
        except urllib.error.URLError as exc:  # pragma: no cover - network edge
            raise TransientTelegramError(str(exc)) from exc
        return {}

    @staticmethod
    def _handle_http_error(exc: urllib.error.HTTPError) -> None:
        body = exc.read().decode("utf-8", errors="ignore")
        if exc.code >= 500:
            raise TransientTelegramError(
                f"telegram 5xx: {exc.code} body={body}"
            ) from exc
        raise SecurityError(f"telegram 4xx: {exc.code} body={body}") from exc


class StubTelegramClient:
    """Deterministic transport used for smoke tests without hitting Telegram."""

    def __init__(self, chat_id: int) -> None:
        self._chat_id = chat_id
        self._log = LOGGER.getChild("telegram.stub")

    async def close(self) -> None:
        return None

    async def get_updates(
        self, *, offset: Optional[int], timeout: int
    ) -> list[dict[str, Any]]:
        await asyncio.sleep(min(1.0, max(0.0, float(timeout))))
        self._log.debug(
            "stub.get_updates",
            extra={"offset": offset, "timeout": timeout},
        )
        return []

    async def send_message(
        self, *, chat_id: int, text: str, parse_mode: str = "MarkdownV2"
    ) -> None:
        self._log.info(
            "stub.send_message",
            extra={
                "chat_id": chat_id,
                "parse_mode": parse_mode,
                "preview": text[:80],
            },
        )
        return None


def build_telegram_client(config: RouterConfig) -> TelegramClient | StubTelegramClient:
    if config.transport_mode == "stub":
        LOGGER.warning(
            "telegram.stub.enabled",
            extra={"chat_id": config.telegram_chat_id},
        )
        return StubTelegramClient(config.telegram_chat_id)
    return TelegramClient(config.telegram_bot_token, api_base=config.telegram_api_base)


def hash_identifier(raw: Any) -> str:
    return uuid.uuid5(uuid.NAMESPACE_OID, str(raw)).hex


def sanitize_message(text: str) -> str:
    sanitized = re.sub(r"\s+", " ", text or "").strip()
    return sanitized[:2000]


class EchoAdapter:
    """Fallback adapter until services/a2a_adapter is implemented."""

    async def invoke(
        self, request: A2ARequest
    ) -> A2AResponse:  # pragma: no cover - placeholder
        now = datetime.now(timezone.utc)
        latency = int((now - request.queue_entered_at).total_seconds() * 1000)
        echoed = (
            f"Persona={request.persona}\n"
            f"Correlation={request.correlation_id}\n"
            f"Prompt={request.prompt[:400]}"
        )
        return A2AResponse(
            final_state="completed",
            text=echoed,
            task_id=request.correlation_id,
            diagnostics={"adapter": "echo"},
            retryable=False,
            latency_ms=latency,
        )


def resolve_adapter() -> RouterAdapter:
    try:
        from services import a2a_adapter as adapter_module  # type: ignore

        if hasattr(adapter_module, "build_adapter"):
            return adapter_module.build_adapter()  # type: ignore[attr-defined]
        if hasattr(adapter_module, "RouterAdapterImpl"):
            return adapter_module.RouterAdapterImpl()  # type: ignore[attr-defined]
    except ImportError:
        LOGGER.info("A2A adapter not found; falling back to echo adapter")
    return EchoAdapter()


class TelegramRouter:
    def __init__(self, config: RouterConfig, adapter: RouterAdapter) -> None:
        self.config = config
        self.adapter = adapter
        self.queue: asyncio.Queue[RouterMessage] = asyncio.Queue(
            maxsize=config.queue_size
        )
        self.raw_updates: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        self.telegram = build_telegram_client(config)
        self.rate_limiter = PersonaRateLimiter(
            config.rate_capacity,
            config.rate_refill_per_min,
            config.commander_capacity,
            config.commander_refill_per_min,
        )
        self.retry_cache = ManualRetryCache(config.retry_cache_size)
        self.shutdown_event = asyncio.Event()
        self.single_flight = asyncio.Semaphore(1)
        self.tasks: list[asyncio.Task[Any]] = []
        self.last_update_id: Optional[int] = None
        self.router_state: Literal["starting", "ready", "draining"] = "starting"
        self.start_time = datetime.now(timezone.utc)
        self.telegram_health = ComponentHealth()
        self.a2a_health = ComponentHealth()
        self.health_server: asyncio.AbstractServer | None = None
        self.health_server_task: asyncio.Task[Any] | None = None
        self.health_path = config.health_path
        self._health_stale_after = max(config.health_interval * 2, 30)

    async def run(self) -> None:
        LOGGER.info("router.start", extra={"queue_size": self.config.queue_size})
        await self._start_health_server()
        self.tasks = [
            asyncio.create_task(self.poll_updates(), name="poll_updates"),
            asyncio.create_task(self.process_updates(), name="process_updates"),
            asyncio.create_task(self.dispatch_queue(), name="dispatch_queue"),
            asyncio.create_task(self.health_task(), name="health_task"),
        ]
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(
                        self.stop(reason=f"signal:{s.name}")
                    ),
                )
        await self.shutdown_event.wait()
        await self._cleanup()

    async def stop(self, reason: str = "requested") -> None:
        if self.shutdown_event.is_set():
            return
        LOGGER.warning("router.stop", extra={"reason": reason})
        self.router_state = "draining"
        self.shutdown_event.set()
        for task in self.tasks:
            task.cancel()

    async def _cleanup(self) -> None:
        for task in self.tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self.health_server:
            self.health_server.close()
            await self.health_server.wait_closed()
        if self.health_server_task:
            self.health_server_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_server_task
        await self.telegram.close()

    async def poll_updates(self) -> None:
        backoff = [1, 3, 7, 15, 30, 60]
        backoff_idx = 0
        while not self.shutdown_event.is_set():
            try:
                updates = await self.telegram.get_updates(
                    offset=self._next_offset(), timeout=self.config.poll_timeout
                )
                self.telegram_health.mark_success()
                for update in updates:
                    await self.raw_updates.put(update)
                    self.last_update_id = update.get("update_id")
                backoff_idx = 0
            except TransientTelegramError as exc:
                self.telegram_health.mark_failure(str(exc))
                wait_for = backoff[min(backoff_idx, len(backoff) - 1)]
                LOGGER.warning(
                    "poll.backoff", extra={"error": str(exc), "sleep": wait_for}
                )
                backoff_idx += 1
                await asyncio.sleep(wait_for)
            except Exception as exc:  # pragma: no cover - defensive
                self.telegram_health.mark_failure(str(exc))
                LOGGER.exception("poll.failed", extra={"error": str(exc)})
                await asyncio.sleep(5)

    def _next_offset(self) -> Optional[int]:
        if self.last_update_id is None:
            return None
        return self.last_update_id + 1

    async def process_updates(self) -> None:
        while not self.shutdown_event.is_set():
            update = await self.raw_updates.get()
            message = update.get("message")
            if not message:
                continue
            try:
                await self._handle_message(
                    update_id=update.get("update_id"), message=message
                )
            except SecurityError as exc:
                LOGGER.warning("security.denied", extra={"error": str(exc)})
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("ingest.failed", extra={"error": str(exc)})

    async def _handle_message(
        self, update_id: int | None, message: dict[str, Any]
    ) -> None:
        if update_id is None:
            raise SecurityError("missing update identifier")
        chat = message.get("chat") or {}
        user = message.get("from") or {}
        chat_id = chat.get("id")
        user_id = user.get("id")
        message_id = message.get("message_id")
        if chat_id is None or user_id is None or message_id is None:
            raise SecurityError("missing chat/user/message identifiers")
        if chat_id != self.config.telegram_chat_id:
            raise SecurityError(f"chat mismatch: {chat_id}")
        user_id_int = int(user_id)
        persona = self._map_persona(user_id_int)
        payload = message.get("text", "")
        if not payload:
            raise SecurityError("empty payload or unsupported message type")
        chat_hash = hash_identifier(chat_id)
        user_hash = hash_identifier(user_id_int)
        message_id_int = int(message_id)
        update_id_int = int(update_id)
        if payload.startswith("/"):
            await self._handle_command(
                CommandMessage(
                    update_id=update_id_int,
                    command=payload.split()[0],
                    args=payload.split()[1:],
                    persona=persona,
                    telegram_message_id=message_id_int,
                    chat_hash=chat_hash,
                    user_hash=user_hash,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            return
        router_msg = RouterMessage(
            update_id=update_id_int,
            persona=persona,
            payload=sanitize_message(payload),
            telegram_message_id=message_id_int,
            chat_hash=chat_hash,
            user_hash=user_hash,
            correlation_id=uuid.uuid4().hex,
        )
        decision = self.rate_limiter.check(persona, user_hash)
        if not decision.allowed:
            await self._send_throttle_notice(router_msg, decision)
            return
        try:
            self.queue.put_nowait(router_msg)
        except asyncio.QueueFull:
            await self._reply(router_msg, "Queue is full, please retry shortly.")
            return
        await self._reply(router_msg, self._accept_message_body(router_msg))

    async def dispatch_queue(self) -> None:
        while not self.shutdown_event.is_set():
            message = await self.queue.get()
            async with self.single_flight:
                await self._invoke_adapter(message)

    async def _invoke_adapter(self, message: RouterMessage) -> None:
        started = datetime.now(timezone.utc)
        request = A2ARequest(
            prompt=message.payload,
            persona=message.persona,
            correlation_id=message.correlation_id,
            telegram_user_hash=message.user_hash,
            queue_entered_at=message.queue_entered_at,
            attempt=message.attempt,
            chat_hash=message.chat_hash,
            telegram_message_id=message.telegram_message_id,
            metadata={
                "queue_depth": self.queue.qsize(),
                "semaphore_slots": getattr(self.single_flight, "_value", 1),
                "router_version": os.getenv("ROUTER_VERSION", "1.0.0"),
            },
        )
        try:
            response = await self.adapter.invoke(request)
            self.a2a_health.mark_success()
        except Exception as exc:
            self.a2a_health.mark_failure(str(exc))
            LOGGER.exception(
                "a2a.invoke.failed",
                extra={"correlation_id": message.correlation_id, "error": str(exc)},
            )
            await self._reply(
                message, "Adapter failure encountered. Operators notified."
            )
            return
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        self.retry_cache.add(
            RetryRecord(
                task_id=response.task_id,
                payload=message.payload,
                persona=message.persona,
                chat_hash=message.chat_hash,
                user_hash=message.user_hash,
                last_final_state=response.final_state,
                diagnostics=response.diagnostics,
                stored_at=datetime.now(timezone.utc),
            )
        )
        await self._reply(message, self._format_final_state(response, elapsed))
        if response.retryable and message.attempt < self.config.retry_attempts:
            LOGGER.info(
                "dispatch.retry",
                extra={
                    "correlation_id": message.correlation_id,
                    "task_id": response.task_id,
                },
            )
            await asyncio.sleep(2**message.attempt)
            await self.queue.put(
                RouterMessage(
                    update_id=message.update_id,
                    persona=message.persona,
                    payload=message.payload,
                    telegram_message_id=message.telegram_message_id,
                    chat_hash=message.chat_hash,
                    user_hash=message.user_hash,
                    correlation_id=uuid.uuid4().hex,
                    attempt=message.attempt + 1,
                )
            )

    async def _handle_command(self, command: CommandMessage) -> None:
        dispatcher = {
            "/status": self._command_status,
            "/retry": self._command_retry,
            "/flush": self._command_flush,
        }.get(command.command.lower())
        if not dispatcher:
            await self._reply_command(command, "Unknown command.")
            return
        await dispatcher(command)

    async def _command_status(self, command: CommandMessage) -> None:
        summary = {
            "queue_depth": self.queue.qsize(),
            "retry_cache": len(self.retry_cache),
            "last_update_id": self.last_update_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        body = "\n".join(f"{k}: {v}" for k, v in summary.items())
        await self._reply_command(command, body)

    async def _command_retry(self, command: CommandMessage) -> None:
        if not command.args:
            await self._reply_command(command, "Usage: /retry <task_id>")
            return
        record = self.retry_cache.get(command.args[0])
        if not record:
            await self._reply_command(command, "Task ID not found or expired.")
            return
        message = RouterMessage(
            update_id=command.update_id,
            persona=record.persona,
            payload=record.payload,
            telegram_message_id=command.telegram_message_id,
            chat_hash=record.chat_hash,
            user_hash=record.user_hash,
            correlation_id=uuid.uuid4().hex,
        )
        await self.queue.put(message)
        await self._reply_command(command, f"Task {record.task_id} requeued.")

    async def _command_flush(self, command: CommandMessage) -> None:
        drained = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        self.retry_cache.clear()
        await self._reply_command(
            command, f"Flushed {drained} queued prompts and cleared retry cache."
        )

    async def health_task(self) -> None:
        while not self.shutdown_event.is_set():
            try:
                await self._probe_adapter_health()
                payload = self._build_health_payload()
                LOGGER.info("health.tick", extra=payload)
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("health.tick.failed", extra={"error": str(exc)})
            await asyncio.sleep(self.config.health_interval)

    async def _start_health_server(self) -> None:
        try:
            self.health_server = await asyncio.start_server(
                self._handle_health_connection,
                host=self.config.health_host,
                port=self.config.health_port,
            )
        except OSError as exc:  # pragma: no cover - bind failures rare
            LOGGER.critical(
                "health.server.bind_failed",
                extra={
                    "error": str(exc),
                    "host": self.config.health_host,
                    "port": self.config.health_port,
                },
            )
            raise
        self.health_server_task = asyncio.create_task(
            self.health_server.serve_forever(), name="health_server"
        )
        LOGGER.info(
            "health.server.start",
            extra={
                "host": self.config.health_host,
                "port": self.config.health_port,
                "path": self.config.health_path,
            },
        )

    async def _handle_health_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_data = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            writer.close()
            await writer.wait_closed()
            return
        request_line = request_data.split(b"\r\n", 1)[0].decode("utf-8", "ignore")
        parts = request_line.split()
        if len(parts) < 2:
            response = self._format_http_response(
                400, b'{"error":"bad request"}', False
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        method, raw_path = parts[0].upper(), parts[1]
        path = raw_path.split("?", 1)[0]
        if path != self.health_path:
            response = self._format_http_response(404, b'{"error":"not found"}', False)
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        if method not in {"GET", "HEAD"}:
            response = self._format_http_response(
                405, b'{"error":"method not allowed"}', False
            )
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
        try:
            payload = self._build_health_payload()
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            include_body = method == "GET"
            response = self._format_http_response(200, body, include_body)
        except Exception as exc:  # pragma: no cover - defensive
            error_body = json.dumps({"error": str(exc)}).encode("utf-8")
            response = self._format_http_response(500, error_body, False)
        writer.write(response)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    def _format_http_response(
        self, status_code: int, body: bytes, include_body: bool
    ) -> bytes:
        reasons = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }
        reason = reasons.get(status_code, "OK")
        headers = [
            f"HTTP/1.1 {status_code} {reason}",
            "Content-Type: application/json",
            "Cache-Control: no-store",
            "Connection: close",
            f"Content-Length: {len(body)}",
            "",
            "",
        ]
        response = "\r\n".join(headers).encode("utf-8")
        if include_body:
            response += body
        return response

    async def _probe_adapter_health(self) -> None:
        probe = getattr(self.adapter, "health_check", None)
        if not callable(probe):
            if self.a2a_health.status != "failed":
                self.a2a_health.mark_success()
            return
        try:
            result = probe()
            if inspect.isawaitable(result):
                result = await result
            if result is False:
                raise RuntimeError("adapter health_check returned false")
            self.a2a_health.mark_success()
        except Exception as exc:  # pragma: no cover - adapter probe errors rare
            self.a2a_health.mark_failure(str(exc))

    def _build_health_payload(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        telegram_payload = self.telegram_health.payload(now, self._health_stale_after)
        a2a_payload = self.a2a_health.payload(now, self._health_stale_after)
        self._update_router_state(telegram_payload["status"], a2a_payload["status"])
        payload = {
            "timestamp": now.isoformat(),
            "status": "ready"
            if self.router_state == "ready"
            else ("draining" if self.router_state == "draining" else "degraded"),
            "router": {
                "state": self.router_state,
                "uptime_seconds": max(0, int((now - self.start_time).total_seconds())),
                "env": os.getenv("ROUTER_ENV", "local"),
                "active": os.getenv("ROUTER_ACTIVE", "true"),
                "last_update_id": self.last_update_id,
            },
            "telegram": telegram_payload,
            "a2a": a2a_payload,
            "queue": {"depth": self.queue.qsize(), "max": self.config.queue_size},
            "retry_cache": {
                "usage": len(self.retry_cache),
                "capacity": self.retry_cache.capacity,
            },
            "persona": {"rate_window": self.rate_limiter.snapshot()},
        }
        return payload

    def _update_router_state(self, telegram_status: str, a2a_status: str) -> None:
        if self.router_state == "draining" or self.shutdown_event.is_set():
            self.router_state = "draining"
            return
        if telegram_status == "ready" and a2a_status == "ready":
            self.router_state = "ready"
        else:
            self.router_state = "starting"

    async def _send_throttle_notice(
        self, message: RouterMessage, decision: RateLimitDecision
    ) -> None:
        text = (
            "Rate limit reached. Please wait"
            f" {int(decision.retry_after)}s before sending another prompt."
        )
        await self._reply(message, text)

    async def _reply(self, message: RouterMessage, body: str) -> None:
        await self.telegram.send_message(
            chat_id=self.config.telegram_chat_id, text=_escape_markdown(body)
        )

    async def _reply_command(self, command: CommandMessage, body: str) -> None:
        await self.telegram.send_message(
            chat_id=self.config.telegram_chat_id, text=_escape_markdown(body)
        )

    def _accept_message_body(self, message: RouterMessage) -> str:
        position = self.queue.qsize()
        return (
            f"Accepted prompt for persona {message.persona}.\n"
            f"Correlation: {message.correlation_id}\n"
            f"Queue position: {position}"
        )

    def _format_final_state(self, response: A2AResponse, latency_ms: int) -> str:
        diagnostics = json.dumps(response.diagnostics)[:400]
        return (
            f"State: {response.final_state}\n"
            f"Task: {response.task_id}\n"
            f"Latency: {latency_ms} ms\n"
            f"Diagnostics: {diagnostics}"
        )

    def _map_persona(self, user_id: int) -> str:
        try:
            persona = self.config.persona_map[int(user_id)]
        except KeyError as exc:
            raise SecurityError(f"user {user_id} not authorized") from exc
        return persona


def _escape_markdown(body: str) -> str:
    return re.sub(r"([_*/`])", r"\\\\1", body)


async def main() -> None:
    configure_logging()
    try:
        config = RouterConfig.load()
    except ConfigError as exc:
        LOGGER.critical("config.invalid", extra={"error": str(exc)})
        raise SystemExit(1) from exc
    adapter = resolve_adapter()
    router = TelegramRouter(config, adapter)
    await router.run()


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


if __name__ == "__main__":
    asyncio.run(main())
