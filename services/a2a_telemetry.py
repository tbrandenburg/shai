"""Telemetry helpers for the A2A adapter."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol


class MetricsClient(Protocol):
    """Minimal metrics surface consumed by the adapter."""

    def increment(self, name: str, *, value: float = 1.0, tags: dict[str, Any] | None = None) -> None: ...

    def observe(self, name: str, *, value: float, tags: dict[str, Any] | None = None) -> None: ...


class NoopMetrics:
    def increment(self, name: str, *, value: float = 1.0, tags: dict[str, Any] | None = None) -> None:  # pragma: no cover - no-op
        return None

    def observe(self, name: str, *, value: float, tags: dict[str, Any] | None = None) -> None:  # pragma: no cover - no-op
        return None


class Tracer(Protocol):
    def start_span(self, name: str, *, attributes: dict[str, Any] | None = None) -> "Span": ...


class Span(Protocol):
    def __enter__(self) -> "Span": ...

    def __exit__(self, exc_type, exc, tb) -> None: ...  # pragma: no cover - structural protocol


class NoopTracer:
    class _Span:
        def __enter__(self) -> "NoopTracer._Span":  # pragma: no cover - no-op
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - no-op
            return None

    def start_span(self, name: str, *, attributes: dict[str, Any] | None = None) -> "NoopTracer._Span":  # pragma: no cover - no-op
        return self._Span()


@dataclass(slots=True)
class TelemetryHandles:
    logger: logging.Logger
    metrics: MetricsClient
    tracer: Tracer

    @classmethod
    def default(cls) -> "TelemetryHandles":
        return cls(
            logger=logging.getLogger("a2a"),
            metrics=NoopMetrics(),
            tracer=NoopTracer(),
        )


def emit_request(telemetry: TelemetryHandles, *, correlation_id: str, persona: str, attempt: int) -> None:
    telemetry.logger.info(
        "a2a.request",
        extra={"correlation_id": correlation_id, "persona": persona, "attempt": attempt},
    )
    telemetry.metrics.increment(
        "a2a_request_total",
        tags={"persona": persona, "attempt": attempt},
    )


def emit_response(
    telemetry: TelemetryHandles,
    *,
    correlation_id: str,
    persona: str,
    attempt: int,
    final_state: str,
    latency_ms: float,
) -> None:
    telemetry.logger.info(
        "a2a.response",
        extra={
            "correlation_id": correlation_id,
            "persona": persona,
            "attempt": attempt,
            "final_state": final_state,
            "latency_ms": latency_ms,
        },
    )
    telemetry.metrics.increment(
        "a2a_response_total",
        tags={"persona": persona, "final_state": final_state},
    )
    telemetry.metrics.observe(
        "a2a_latency_ms",
        value=latency_ms,
        tags={"persona": persona},
    )


def emit_failure(
    telemetry: TelemetryHandles,
    *,
    correlation_id: str,
    persona: str,
    attempt: int,
    reason: str,
    retryable: bool,
) -> None:
    telemetry.logger.error(
        "a2a.failure",
        extra={
            "correlation_id": correlation_id,
            "persona": persona,
            "attempt": attempt,
            "reason": reason,
            "retryable": retryable,
        },
    )
    metric = "a2a_transient_error_total" if retryable else "a2a_fatal_error_total"
    telemetry.metrics.increment(metric, tags={"persona": persona})


def emit_retry(
    telemetry: TelemetryHandles,
    *,
    correlation_id: str,
    persona: str,
    attempt: int,
    wait_s: float,
) -> None:
    telemetry.logger.info(
        "a2a.retry",
        extra={
            "correlation_id": correlation_id,
            "persona": persona,
            "attempt": attempt,
            "wait_s": round(wait_s, 3),
        },
    )
    telemetry.metrics.increment("a2a_retry_total", tags={"persona": persona})


def emit_timeout(telemetry: TelemetryHandles, *, correlation_id: str, persona: str) -> None:
    telemetry.logger.warning(
        "a2a.timeout",
        extra={"correlation_id": correlation_id, "persona": persona, "ts": time.time()},
    )
    telemetry.metrics.increment("a2a_timeout_total", tags={"persona": persona})
