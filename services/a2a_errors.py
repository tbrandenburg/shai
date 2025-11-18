"""Exception hierarchy for the A2A integration stack."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


class A2AError(Exception):
    """Base error for adapter/integration failures."""


class ConfigError(A2AError):
    """Raised when configuration validation fails."""


@dataclass(slots=True)
class A2AAdapterError(A2AError):
    """Wraps transport-level issues surfaced by the upstream client."""

    message: str
    recoverable: bool = True
    http_status: int | None = None
    metadata: dict[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - basic repr
        base = self.message
        if self.http_status:
            base = f"{base} (status={self.http_status})"
        if self.metadata:
            base = f"{base} meta={self.metadata}"
        return base


@dataclass(slots=True)
class A2AIntegrationError(A2AError):
    """Raised when orchestration logic determines a fatal outcome."""

    classification: Literal["fatal", "transient", "config"]
    message: str
    task_id: str | None = None
    attempt_count: int = 0
    metadata: dict[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - basic repr
        return f"{self.classification}: {self.message}"
