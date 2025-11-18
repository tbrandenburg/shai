from datetime import datetime, timezone
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from bots import telegram_router as router_mod
from services import a2a_adapter
from services.a2a_adapter import A2AIntegrationService, A2ATaskOutcome
from services.a2a_config import A2AConfig
from services.a2a_errors import A2AAdapterError
from services.a2a_telemetry import TelemetryHandles


class FakeTransport(a2a_adapter.Fasta2AClientAdapter):
    def __init__(
        self,
        config: A2AConfig,
        telemetry: TelemetryHandles,
        *,
        outcomes: list[A2ATaskOutcome] | None = None,
        errors: list[A2AAdapterError] | None = None,
    ) -> None:
        super().__init__(config, telemetry)
        self._outcomes = list(outcomes or [])
        self._errors = list(errors or [])
        self.calls: list[a2a_adapter.A2AAdapterRequest] = []

    async def run(self, request: a2a_adapter.A2AAdapterRequest) -> A2ATaskOutcome:
        self.calls.append(request)
        if self._errors:
            raise self._errors.pop(0)
        if not self._outcomes:
            raise AssertionError("No more fake outcomes configured")
        return self._outcomes.pop(0)


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fast_sleep(delay: float) -> None:  # pragma: no cover - helper
        return None

    monkeypatch.setattr(a2a_adapter.asyncio, "sleep", _fast_sleep)


@pytest.fixture()
def adapter_config() -> A2AConfig:
    return A2AConfig(
        base_url="https://api.example.com",
        api_key=None,
        poll_interval_s=0.05,
        poll_timeout_s=1.0,
        retry_limit=2,
        retry_backoff_s=0.01,
        retry_backoff_multiplier=1.0,
        retry_backoff_max_s=0.02,
        allowed_persona_tags=frozenset({"Operator", "OnCall", "IncidentCommander", "AutomationAuditor"}),
        allow_insecure=False,
        environment="test",
        compliance_tags={"region": "us-east-1", "classification": "confidential"},
    )


@pytest.fixture()
def router_request() -> router_mod.A2ARequest:
    return router_mod.A2ARequest(
        prompt="Deploy build",
        persona="operator",
        correlation_id="corr-123",
        telegram_user_hash="user-hash",
        queue_entered_at=datetime.now(timezone.utc),
        attempt=1,
        chat_hash="chat-hash",
    )


def _service(
    config: A2AConfig,
    *,
    outcomes: list[A2ATaskOutcome] | None = None,
    errors: list[A2AAdapterError] | None = None,
) -> tuple[A2AIntegrationService, FakeTransport]:
    telemetry = TelemetryHandles.default()
    transport = FakeTransport(config, telemetry, outcomes=outcomes, errors=errors)
    service = A2AIntegrationService(config=config, telemetry=telemetry, transport=transport)
    return service, transport


@pytest.mark.asyncio
async def test_integration_success_returns_completed_response(adapter_config: A2AConfig, router_request: router_mod.A2ARequest) -> None:
    outcome = A2ATaskOutcome(
        task_id="task-1",
        final_state="completed",
        attempt_count=1,
        latency_ms=1200,
        server_messages=["done"],
        artifacts=["analysis"],
        upstream_state={"state": "completed"},
        retryable=False,
    )
    service, transport = _service(adapter_config, outcomes=[outcome])

    response = await service.invoke(router_request)

    assert response.final_state == "completed"
    assert response.text == "analysis"
    assert not response.retryable
    assert transport.calls
    envelope = transport.calls[0].envelope
    assert envelope.persona_tag == "Operator"
    assert envelope.telemetry["environment"] == adapter_config.environment


@pytest.mark.asyncio
async def test_integration_retries_transient_outcome(adapter_config: A2AConfig, router_request: router_mod.A2ARequest) -> None:
    transient = A2ATaskOutcome(
        task_id="task-2",
        final_state="canceled",
        attempt_count=1,
        latency_ms=500,
        server_messages=["still working"],
        artifacts=[],
        upstream_state={"state": "canceled"},
        retryable=True,
    )
    success = A2ATaskOutcome(
        task_id="task-2",
        final_state="completed",
        attempt_count=2,
        latency_ms=900,
        server_messages=["ready"],
        artifacts=["result"],
        upstream_state={"state": "completed"},
        retryable=False,
    )
    service, transport = _service(adapter_config, outcomes=[transient, success])

    response = await service.invoke(router_request)

    assert response.final_state == "completed"
    assert len(transport.calls) == 2
    assert transport.calls[0].attempt == 1
    assert transport.calls[1].attempt == 2


@pytest.mark.asyncio
async def test_integration_surfaces_fatal_error(adapter_config: A2AConfig, router_request: router_mod.A2ARequest) -> None:
    error = A2AAdapterError("boom", recoverable=False)
    service, transport = _service(adapter_config, errors=[error])

    response = await service.invoke(router_request)

    assert response.final_state == "failed"
    assert "boom" in response.text
    assert not response.retryable
    assert len(transport.calls) == 1
