"""Configuration helpers for the A2A adapter."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import FrozenSet
from urllib.parse import urlparse

from .a2a_errors import ConfigError


DEFAULT_PERSONAS = frozenset({"Operator", "OnCall", "IncidentCommander", "AutomationAuditor"})


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - invalid env
        raise ConfigError(f"Invalid datetime for A2A_API_KEY_ISSUED_AT: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_persona_tags(raw: str | None) -> FrozenSet[str]:
    if not raw:
        return DEFAULT_PERSONAS
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            values = [str(item) for item in parsed]
        elif isinstance(parsed, dict):
            values = [str(key) for key in parsed.keys()]
        else:
            values = [str(parsed)]
    except json.JSONDecodeError:
        values = [segment.strip() for segment in raw.split(",") if segment.strip()]
    normalized = {value if value[0].isupper() else value.title() for value in values}
    return frozenset(normalized) if normalized else DEFAULT_PERSONAS


@dataclass(slots=True)
class A2AConfig:
    base_url: str
    api_key: str | None
    poll_interval_s: float = 2.0
    poll_timeout_s: float = 30.0
    retry_limit: int = 1
    retry_backoff_s: float = 2.0
    retry_backoff_multiplier: float = 2.0
    retry_backoff_max_s: float = 8.0
    allowed_persona_tags: FrozenSet[str] = DEFAULT_PERSONAS
    api_key_issued_at: datetime | None = None
    allow_insecure: bool = False
    environment: str = "dev"
    compliance_tags: dict | None = None

    @property
    def max_polls(self) -> int:
        return max(1, int(self.poll_timeout_s // max(self.poll_interval_s, 0.1)))

    @property
    def jitter_bounds(self) -> tuple[float, float]:
        spread = 0.2 * self.poll_interval_s
        return (-spread, spread)

    def sla_budget(self, *, persona: str | None = None) -> float:
        persona = (persona or "" ).lower()
        if persona == "incidentcommander" or persona == "incident_commander":
            return 8.0
        if persona == "automationauditor" or persona == "automation_auditor":
            return 10.0
        return 12.0


KEY_MAX_AGE_DAYS = 90
KEY_WARN_DAYS = 75


def load_a2a_config() -> A2AConfig:
    base_url = os.getenv("A2A_BASE_URL")
    if not base_url:
        raise ConfigError("A2A_BASE_URL is required")
    parsed = urlparse(base_url)
    allow_insecure = _parse_bool(os.getenv("A2A_ALLOW_INSECURE"))
    if parsed.scheme != "https" and not allow_insecure:
        raise ConfigError("A2A_BASE_URL must be https unless A2A_ALLOW_INSECURE is true")
    api_key = os.getenv("A2A_API_KEY") or None
    poll_interval = float(os.getenv("A2A_POLL_INTERVAL_SECONDS", 2.0))
    poll_timeout = float(os.getenv("A2A_POLL_TIMEOUT_SECONDS", 30.0))
    retry_limit = int(os.getenv("A2A_RETRY_LIMIT", 1))
    retry_backoff = float(os.getenv("A2A_RETRY_BACKOFF_SECONDS", 2.0))
    retry_multiplier = float(os.getenv("A2A_RETRY_BACKOFF_MULTIPLIER", 2.0))
    retry_max = float(os.getenv("A2A_RETRY_BACKOFF_MAX_SECONDS", 8.0))
    allowed_tags = _parse_persona_tags(os.getenv("A2A_ALLOWED_PROMPT_TAGS"))
    issued_at = _parse_datetime(os.getenv("A2A_API_KEY_ISSUED_AT"))
    environment = os.getenv("A2A_ENVIRONMENT", os.getenv("ENVIRONMENT", "dev"))
    compliance = _parse_json(os.getenv("A2A_COMPLIANCE_TAGS")) or {
        "region": os.getenv("A2A_REGION", "us-east-1"),
        "classification": os.getenv("A2A_CLASSIFICATION", "confidential"),
    }
    if issued_at:
        age_days = (datetime.now(timezone.utc) - issued_at).days
        if age_days > KEY_MAX_AGE_DAYS:
            raise ConfigError("A2A_API_KEY is older than 90 days; rotate before deploying")
        if age_days > KEY_WARN_DAYS:
            logging = __import__("logging")
            logging.getLogger("a2a").warning("A2A_API_KEY older than 75 days", extra={"age_days": age_days})
    return A2AConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        poll_interval_s=poll_interval,
        poll_timeout_s=poll_timeout,
        retry_limit=max(0, retry_limit),
        retry_backoff_s=retry_backoff,
        retry_backoff_multiplier=max(1.0, retry_multiplier),
        retry_backoff_max_s=max(retry_backoff, retry_max),
        allowed_persona_tags=allowed_tags,
        api_key_issued_at=issued_at,
        allow_insecure=allow_insecure,
        environment=environment,
        compliance_tags=compliance,
    )
