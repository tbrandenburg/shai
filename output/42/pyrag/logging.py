"""Structured logging helpers for pyrag."""

from __future__ import annotations

import logging

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


def _normalize_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return logging.INFO
