"""Structured logging helpers for pyrag."""

from __future__ import annotations

import json
import logging
from typing import Any

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DEFAULT_LEVEL = "INFO"
_CONFIGURED = False


def configure(level: str = _DEFAULT_LEVEL) -> None:
    """Initialize the root logger and update the current level."""

    global _CONFIGURED
    numeric_level = _normalize_level(level)
    if not _CONFIGURED:
        logging.basicConfig(level=numeric_level, format=_LOG_FORMAT)
        _CONFIGURED = True
    logging.getLogger().setLevel(numeric_level)


def configure_json(level: str = _DEFAULT_LEVEL) -> None:
    """Switch logging to a JSON formatter for downstream ingestion."""

    global _CONFIGURED
    numeric_level = _normalize_level(level)
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger scoped to the requested module."""

    if not _CONFIGURED:
        configure()
    return logging.getLogger(name)


def redact_uri(uri: str | None) -> str:
    """Hide credentials embedded in connection URIs for safe logging."""

    if not uri:
        return ""
    if "@" not in uri:
        return uri
    prefix, suffix = uri.split("@", 1)
    if "//" in prefix:
        scheme, _credentials = prefix.split("//", 1)
        return f"{scheme}//***@{suffix}"
    return f"***@{suffix}"


def safe_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """Ensure log extra payloads are JSON serializable."""

    sanitized: dict[str, Any] = {}
    for key, value in extra.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


def _normalize_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return logging.INFO


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - formatting helper
        payload = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in {
                "args",
                "msg",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue
            payload[key] = value
        return json.dumps(payload, default=str)
