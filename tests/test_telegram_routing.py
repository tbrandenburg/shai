import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from bots import telegram_router as router_mod


VALID_TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd"


class FakeTelegram:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    async def send_message(
        self, *, chat_id: int, text: str, parse_mode: str = "MarkdownV2"
    ) -> None:
        self.sent_messages.append(
            {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        )

    async def get_updates(
        self, *, offset: int | None, timeout: int
    ) -> list[dict]:  # pragma: no cover - unused
        return []


class FakeAdapter:
    def __init__(self, *, response: router_mod.A2AResponse | None = None) -> None:
        self.response = response or router_mod.A2AResponse(
            final_state="completed",
            text="done",
            task_id="task-123",
            diagnostics={"adapter": "fake"},
            retryable=True,
            latency_ms=42,
        )
        self.calls: list[router_mod.A2ARequest] = []

    async def invoke(self, request: router_mod.A2ARequest) -> router_mod.A2AResponse:
        self.calls.append(request)
        return self.response


class StubRateLimiter:
    def __init__(self, decisions: list[router_mod.RateLimitDecision]) -> None:
        self.decisions = decisions
        self.calls: list[tuple[str, str]] = []

    def check(
        self, persona: str, user_hash: str, now: datetime | None = None
    ) -> router_mod.RateLimitDecision:
        self.calls.append((persona, user_hash))
        if self.decisions:
            return self.decisions.pop(0)
        return router_mod.RateLimitDecision(True)

    def snapshot(self) -> dict[str, Any]:
        return {
            "tracked": len(self.calls),
            "default_capacity": 0,
            "default_refill_per_min": 0,
            "commander_capacity": 0,
            "commander_refill_per_min": 0,
        }


@pytest.fixture()
def router_config() -> router_mod.RouterConfig:
    return router_mod.RouterConfig(
        telegram_bot_token=VALID_TOKEN,
        telegram_chat_id=999,
        persona_map={111: "operator"},
        queue_size=10,
        poll_timeout=5,
        retry_attempts=2,
        rate_capacity=2,
        rate_refill_per_min=6,
        commander_capacity=4,
        commander_refill_per_min=12,
        health_interval=1,
        retry_cache_size=5,
    )


def build_router(
    config: router_mod.RouterConfig,
    *,
    rate_decisions: list[router_mod.RateLimitDecision] | None = None,
) -> tuple[router_mod.TelegramRouter, FakeTelegram]:
    adapter = FakeAdapter()
    router = router_mod.TelegramRouter(config, adapter)
    fake_telegram = FakeTelegram()
    router.telegram = cast(router_mod.TelegramClient, fake_telegram)
    router.rate_limiter = cast(
        router_mod.PersonaRateLimiter,
        StubRateLimiter(rate_decisions or [router_mod.RateLimitDecision(True)]),
    )
    return router, fake_telegram


@pytest.mark.asyncio
async def test_handle_message_enqueues_and_replies(
    router_config: router_mod.RouterConfig,
) -> None:
    router, fake_telegram = build_router(router_config)
    message = {
        "chat": {"id": router_config.telegram_chat_id},
        "from": {"id": 111},
        "message_id": 55,
        "text": "  ping   world  ",
    }

    await router._handle_message(update_id=101, message=message)

    assert router.queue.qsize() == 1
    queued = router.queue.get_nowait()
    assert queued.payload == "ping world"
    assert fake_telegram.sent_messages, "Router should acknowledge accepted prompt"
    assert "Accepted prompt" in fake_telegram.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_handle_message_rate_limited_sends_notice(
    router_config: router_mod.RouterConfig,
) -> None:
    decision = router_mod.RateLimitDecision(False, retry_after=7, violation_count=2)
    router, fake_telegram = build_router(router_config, rate_decisions=[decision])
    message = {
        "chat": {"id": router_config.telegram_chat_id},
        "from": {"id": 111},
        "message_id": 77,
        "text": "hello",
    }

    await router._handle_message(update_id=202, message=message)

    assert router.queue.qsize() == 0
    assert "Rate limit" in fake_telegram.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_command_retry_requeues_from_cache(
    router_config: router_mod.RouterConfig,
) -> None:
    router, fake_telegram = build_router(router_config)
    record = router_mod.RetryRecord(
        task_id="abc",
        payload="payload",
        persona="operator",
        chat_hash="chat",
        user_hash="user",
        last_final_state="failed",
        diagnostics={"reason": "timeout"},
        stored_at=datetime.now(timezone.utc),
    )
    router.retry_cache.add(record)

    command = router_mod.CommandMessage(
        update_id=404,
        command="/retry",
        args=["abc"],
        persona="operator",
        telegram_message_id=88,
        chat_hash="chat",
        user_hash="user",
        timestamp=datetime.now(timezone.utc),
    )

    await router._command_retry(command)

    assert router.queue.qsize() == 1
    assert "requeued" in fake_telegram.sent_messages[-1]["text"]


@pytest.mark.asyncio
async def test_invoke_adapter_persists_final_state_and_schedules_retry(
    router_config: router_mod.RouterConfig,
) -> None:
    router, fake_telegram = build_router(router_config)
    router.rate_limiter = cast(
        router_mod.PersonaRateLimiter,
        StubRateLimiter([router_mod.RateLimitDecision(True)]),
    )
    router.queue = asyncio.Queue(maxsize=router_config.queue_size)
    message = router_mod.RouterMessage(
        update_id=1,
        persona="operator",
        payload="ping",
        telegram_message_id=11,
        chat_hash="chat",
        user_hash="user",
        correlation_id="corr",
    )

    await router._invoke_adapter(message)

    assert len(router.retry_cache) == 1
    assert fake_telegram.sent_messages, "Final state message should be sent"
    assert "State" in fake_telegram.sent_messages[-1]["text"]
    retry_message = await router.queue.get()
    assert retry_message.attempt == 2


@pytest.mark.asyncio
async def test_health_payload_reflects_ready_state(
    router_config: router_mod.RouterConfig,
) -> None:
    router, _ = build_router(router_config)
    router.telegram_health.mark_success()
    router.a2a_health.mark_success()

    payload = router._build_health_payload()

    assert payload["router"]["state"] == "ready"
    assert payload["telegram"]["status"] == "ready"
    assert payload["queue"]["depth"] == 0


@pytest.mark.asyncio
async def test_probe_adapter_health_uses_health_check(
    router_config: router_mod.RouterConfig,
) -> None:
    class HealthCheckedAdapter(FakeAdapter):
        def __init__(self) -> None:
            super().__init__()
            self.health_calls = 0

        async def health_check(self) -> bool:
            self.health_calls += 1
            return True

    adapter = HealthCheckedAdapter()
    router = router_mod.TelegramRouter(router_config, adapter)
    router.telegram = cast(router_mod.TelegramClient, FakeTelegram())

    await router._probe_adapter_health()
    payload = router._build_health_payload()

    assert adapter.health_calls == 1
    assert payload["a2a"]["status"] == "ready"
