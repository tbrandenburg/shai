"""A2A adapter and integration implementation."""
from __future__ import annotations

import asyncio
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, TYPE_CHECKING, cast

from .a2a_config import A2AConfig, load_a2a_config
from .a2a_errors import A2AAdapterError
from .a2a_metadata import A2AEnvelopedRequest, MetadataComposer, RouterCommand
from .a2a_telemetry import (
    TelemetryHandles,
    emit_failure,
    emit_request,
    emit_response,
    emit_retry,
    emit_timeout,
)

try:  # pragma: no cover - optional for tests
    from bots import telegram_router as router_module
    RouterResponseBase = router_module.A2AResponse  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - import guard
    router_module = None

    @dataclass(slots=True)
    class RouterResponseBase:
        final_state: str
        text: str
        task_id: str
        diagnostics: dict[str, Any]
        retryable: bool
        latency_ms: int

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bots.telegram_router import A2ARequest as RouterA2ARequest
else:
    RouterA2ARequest = Any


@dataclass(slots=True)
class A2AAdapterRequest:
    envelope: A2AEnvelopedRequest
    config: A2AConfig
    attempt: int = 1


@dataclass(slots=True)
class A2ATaskOutcome:
    task_id: str
    final_state: Literal["completed", "failed", "canceled", "rejected", "timeout"]
    attempt_count: int
    latency_ms: int
    server_messages: list[str]
    artifacts: list[str]
    upstream_state: dict[str, Any]
    retryable: bool = False


class SimpleFasta2AClient:
    """Lightweight HTTP client mirroring `fasta2a_client.py` semantics."""

    def __init__(self, *, base_url: str, api_key: str | None, allow_insecure: bool) -> None:
        self._base_url = base_url.rstrip("/")
        self._allow_insecure = allow_insecure
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def send_message(self, message_payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps({"message": message_payload}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/send_message",
            data=body,
            method="POST",
            headers=self._headers,
        )
        return self._execute(request)

    def get_task(self, task_id: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(task_id, safe="")
        request = urllib.request.Request(
            f"{self._base_url}/tasks/{encoded}",
            method="GET",
            headers=self._headers,
        )
        return self._execute(request)

    def _execute(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw or "{}")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network edge
            body = exc.read().decode("utf-8", errors="ignore")
            raise A2AAdapterError(
                f"Upstream HTTP error {exc.code}",
                recoverable=exc.code >= 500 or exc.code == 429,
                http_status=exc.code,
                metadata={"body": body[:400]},
            ) from exc
        except urllib.error.URLError as exc:  # pragma: no cover - network edge
            raise A2AAdapterError("Network error", metadata={"reason": str(exc)}) from exc
        except json.JSONDecodeError as exc:  # pragma: no cover - upstream bug
            raise A2AAdapterError("Invalid JSON payload from upstream", recoverable=False) from exc


class Fasta2AClientAdapter:
    FINAL_STATES = {"completed", "failed", "canceled", "rejected"}

    def __init__(
        self,
        config: A2AConfig,
        telemetry: TelemetryHandles,
        *,
        client: SimpleFasta2AClient | None = None,
    ) -> None:
        self.config = config
        self.telemetry = telemetry
        self._client = client or SimpleFasta2AClient(
            base_url=config.base_url,
            api_key=config.api_key,
            allow_insecure=config.allow_insecure,
        )

    async def run(self, request: A2AAdapterRequest) -> A2ATaskOutcome:
        message_payload = self._build_message(request.envelope)
        send_started = time.monotonic()
        response = await asyncio.to_thread(self._client.send_message, message_payload)
        task_id = str(response.get("task_id", "")).strip()
        if not task_id:
            raise A2AAdapterError("Upstream response missing task_id", recoverable=False)
        latency_ms = int((time.monotonic() - send_started) * 1000)
        final_state_literal: Literal["completed", "failed", "canceled", "rejected", "timeout"] | None = None
        server_messages: list[str] = []
        artifacts: list[str] = []
        upstream_state: dict[str, Any] = {"task_id": task_id}
        polls = 0
        deadline = time.monotonic() + request.config.poll_timeout_s
        while True:
            if time.monotonic() >= deadline or polls >= request.config.max_polls:
                raise A2AAdapterError("Polling exceeded timeout", metadata={"task_id": task_id})
            snapshot = await asyncio.to_thread(self._client.get_task, task_id)
            polls += 1
            upstream_state = snapshot or {"state": "unknown"}
            state = str(upstream_state.get("state", "in_progress")).lower()
            server_messages = [str(msg) for msg in upstream_state.get("messages", [])]
            artifacts = self._extract_artifacts(upstream_state.get("artifacts", []))
            attempt_count = int(upstream_state.get("attempt_count") or polls)
            if state in self.FINAL_STATES:
                final_state_literal = cast(
                    Literal["completed", "failed", "canceled", "rejected", "timeout"],
                    state,
                )
                break
            await asyncio.sleep(self._next_sleep())
        total_latency = int((time.monotonic() - send_started) * 1000)
        if final_state_literal is None:
            final_state_literal = cast(Literal["completed", "failed", "canceled", "rejected", "timeout"], "timeout")
        retryable = final_state_literal in {"canceled"}
        return A2ATaskOutcome(
            task_id=task_id,
            final_state=final_state_literal,
            attempt_count=attempt_count,
            latency_ms=total_latency,
            server_messages=server_messages,
            artifacts=artifacts,
            upstream_state=upstream_state,
            retryable=retryable,
        )

    def _build_message(self, envelope: A2AEnvelopedRequest) -> dict[str, Any]:
        part_metadata = {
            "correlation_id": envelope.correlation_id,
            "persona_tag": envelope.persona_tag,
            "prompt_checksum": envelope.prompt_checksum,
            "redaction_rules": envelope.redaction_rules,
        }
        message_metadata = {
            "correlation_id": envelope.correlation_id,
            "chat_hash": envelope.chat_hash,
            "user_hash": envelope.user_hash,
            "received_at": envelope.received_at.isoformat(),
            "telemetry": envelope.telemetry,
            "compliance_tags": envelope.compliance_tags,
            "persona_context": envelope.persona_context,
            "trace": envelope.trace,
            "envelope_version": envelope.envelope_version,
        }
        return {
            "role": "user",
            "kind": "message",
            "message_id": envelope.message_id,
            "metadata": message_metadata,
            "parts": [
                {
                    "kind": "text",
                    "text": envelope.sanitized_text,
                    "metadata": part_metadata,
                }
            ],
        }

    def _extract_artifacts(self, artifacts: list[Any]) -> list[str]:
        normalized: list[str] = []
        for artifact in artifacts:
            if isinstance(artifact, str):
                normalized.append(artifact)
            elif isinstance(artifact, dict) and "text" in artifact:
                normalized.append(str(artifact.get("text")))
        return normalized

    def _next_sleep(self) -> float:
        jitter_low, jitter_high = self.config.jitter_bounds
        return max(0.1, self.config.poll_interval_s + random.uniform(jitter_low, jitter_high))


class A2AIntegrationService:
    def __init__(
        self,
        *,
        config: A2AConfig,
        telemetry: TelemetryHandles,
        transport: Fasta2AClientAdapter | None = None,
    ) -> None:
        self.config = config
        self.telemetry = telemetry
        self.transport = transport or Fasta2AClientAdapter(config, telemetry)
        self.composer = MetadataComposer(config)

    async def invoke(self, request: RouterA2ARequest) -> RouterResponseBase:
        command = self._command_from_request(request)
        envelope = self.composer.compose(command)
        attempt = 1
        max_auto_retries = self._auto_retry_budget(envelope.persona_tag)
        deadline = time.monotonic() + self.config.sla_budget(persona=envelope.persona_tag)
        while True:
            adapter_request = A2AAdapterRequest(envelope=envelope, config=self.config, attempt=attempt)
            emit_request(self.telemetry, correlation_id=envelope.correlation_id, persona=envelope.persona_tag, attempt=attempt)
            try:
                outcome = await self.transport.run(adapter_request)
            except A2AAdapterError as exc:
                emit_failure(
                    self.telemetry,
                    correlation_id=envelope.correlation_id,
                    persona=envelope.persona_tag,
                    attempt=attempt,
                    reason=exc.message,
                    retryable=exc.recoverable,
                )
                if not exc.recoverable or attempt > max_auto_retries:
                    return self._build_error_response(
                        envelope,
                        classification="fatal" if not exc.recoverable else "transient",
                        message=exc.message,
                        task_id=exc.metadata.get("task_id") if exc.metadata else None,
                        retryable=exc.recoverable,
                    )
                wait_s = self._backoff(attempt)
                emit_retry(self.telemetry, correlation_id=envelope.correlation_id, persona=envelope.persona_tag, attempt=attempt, wait_s=wait_s)
                await asyncio.sleep(wait_s)
                attempt += 1
                continue

            emit_response(
                self.telemetry,
                correlation_id=envelope.correlation_id,
                persona=envelope.persona_tag,
                attempt=attempt,
                final_state=outcome.final_state,
                latency_ms=outcome.latency_ms,
            )

            if outcome.final_state == "completed":
                return self._build_success_response(envelope, outcome)
            if outcome.final_state in {"failed", "rejected"}:
                return self._build_error_response(
                    envelope,
                    classification="fatal",
                    message="Upstream reported failure",
                    task_id=outcome.task_id,
                    retryable=False,
                    upstream=outcome.upstream_state,
                )
            timed_out = time.monotonic() >= deadline
            if attempt > max_auto_retries or timed_out or not outcome.retryable:
                if timed_out:
                    emit_timeout(self.telemetry, correlation_id=envelope.correlation_id, persona=envelope.persona_tag)
                return self._build_error_response(
                    envelope,
                    classification="transient",
                    message="A2A task still running",
                    task_id=outcome.task_id,
                    retryable=not timed_out,
                    upstream=outcome.upstream_state,
                )
            wait_s = self._backoff(attempt)
            emit_retry(self.telemetry, correlation_id=envelope.correlation_id, persona=envelope.persona_tag, attempt=attempt, wait_s=wait_s)
            await asyncio.sleep(wait_s)
            attempt += 1

    def _build_success_response(self, envelope: A2AEnvelopedRequest, outcome: A2ATaskOutcome) -> RouterResponseBase:
        text = outcome.artifacts[0] if outcome.artifacts else "\n".join(outcome.server_messages) or "A2A completed"
        diagnostics = {
            "persona": envelope.persona_tag,
            "attempt_count": outcome.attempt_count,
            "final_state": outcome.final_state,
            "server_messages": outcome.server_messages,
            "trace": envelope.trace,
        }
        return self._response(
            final_state="completed",
            text=text,
            task_id=outcome.task_id,
            diagnostics=diagnostics,
            retryable=False,
            latency_ms=outcome.latency_ms,
        )

    def _build_error_response(
        self,
        envelope: A2AEnvelopedRequest,
        *,
        classification: Literal["fatal", "transient"],
        message: str,
        task_id: str | None,
        retryable: bool,
        upstream: dict[str, Any] | None = None,
    ) -> RouterResponseBase:
        final_state = "failed" if classification == "fatal" else "canceled"
        diagnostics = {
            "persona": envelope.persona_tag,
            "classification": classification,
            "upstream": upstream or {},
        }
        return self._response(
            final_state=final_state,
            text=message,
            task_id=task_id or envelope.correlation_id,
            diagnostics=diagnostics,
            retryable=retryable,
            latency_ms=0,
        )

    def _command_from_request(self, request: RouterA2ARequest) -> RouterCommand:
        metadata = getattr(request, "metadata", {}) or {}
        queue_depth = int(metadata.get("queue_depth", 0))
        semaphore_slots = int(metadata.get("semaphore_slots", 1))
        duty_status = self._duty_status(request.persona)
        persona_context = {
            "telegram_user_hash": request.telegram_user_hash,
            "queue_entered_at": request.queue_entered_at.isoformat(),
        }
        if request.chat_hash:
            persona_context["chat_hash"] = request.chat_hash
        redaction_rules = metadata.get("redaction_rules", ["telegram-router-sanitize"])
        telemetry = {
            "source": metadata.get("source", "telegram_router"),
            "version": metadata.get("router_version", "1.0.0"),
            "environment": self.config.environment,
        }
        return RouterCommand(
            correlation_id=request.correlation_id,
            chat_hash=request.chat_hash or "na",
            user_hash=request.telegram_user_hash,
            persona_tag=request.persona,
            duty_status=duty_status,
            sanitized_text=request.prompt,
            received_at=request.queue_entered_at,
            queue_depth=queue_depth,
            semaphore_slots=semaphore_slots,
            telemetry=telemetry,
            compliance_tags=self.config.compliance_tags or {},
            redaction_rules=list(redaction_rules),
            persona_context=persona_context,
        )

    def _auto_retry_budget(self, persona: str) -> int:
        key = persona.lower().replace("_", "")
        if key == "operator":
            return min(2, self.config.retry_limit + 1)
        if key == "oncall":
            return min(1, self.config.retry_limit)
        return 0

    def _duty_status(self, persona: str) -> str:
        slug = persona.lower().replace("_", "")
        if slug == "operator":
            return "primary"
        if slug == "oncall":
            return "secondary"
        if slug == "incidentcommander":
            return "sev1"
        if slug == "automationauditor":
            return "audit"
        return "primary"

    def _backoff(self, attempt: int) -> float:
        base = self.config.retry_backoff_s * (self.config.retry_backoff_multiplier ** (attempt - 1))
        bounded = min(base, self.config.retry_backoff_max_s)
        jitter = random.uniform(-0.2, 0.2) * bounded
        return max(0.5, bounded + jitter)

    def _response(
        self,
        *,
        final_state: str,
        text: str,
        task_id: str,
        diagnostics: dict[str, Any],
        retryable: bool,
        latency_ms: int,
    ) -> RouterResponseBase:
        return RouterResponseBase(
            final_state=final_state,
            text=text,
            task_id=task_id,
            diagnostics=diagnostics,
            retryable=retryable,
            latency_ms=latency_ms,
        )


def build_adapter(*, config: A2AConfig | None = None, telemetry: TelemetryHandles | None = None) -> A2AIntegrationService:
    config = config or load_a2a_config()
    telemetry = telemetry or TelemetryHandles.default()
    return A2AIntegrationService(config=config, telemetry=telemetry)
