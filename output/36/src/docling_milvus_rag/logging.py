"""Structured logging helpers."""

from __future__ import annotations

import logging
from typing import Any

import structlog

DEFAULT_LOGGING_LEVEL = logging.INFO


def _coerce_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        numeric = getattr(logging, level.upper(), None)
        if isinstance(numeric, int):
            return numeric
    return DEFAULT_LOGGING_LEVEL


def configure_logging(json_logs: bool = False, level: str | int = DEFAULT_LOGGING_LEVEL) -> None:
    """Configure structlog + stdlib logging only once."""

    if getattr(configure_logging, "_configured", False):  # type: ignore[attr-defined]
        return

    numeric_level = _coerce_level(level)
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
    )

    logging.basicConfig(level=numeric_level)
    setattr(configure_logging, "_configured", True)


def get_logger(name: str = "docling_milvus_rag") -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger."""

    return structlog.get_logger(name)
