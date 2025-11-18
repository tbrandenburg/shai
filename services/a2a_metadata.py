"""Metadata envelope composition helpers."""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .a2a_config import A2AConfig
from .a2a_errors import ConfigError


@dataclass(slots=True)
class RouterCommand:
    correlation_id: str
    chat_hash: str
    user_hash: str
    persona_tag: str
    duty_status: str
    sanitized_text: str
    received_at: datetime
    queue_depth: int
    semaphore_slots: int
    telemetry: dict[str, Any]
    compliance_tags: dict[str, Any]
    redaction_rules: list[str] = field(default_factory=list)
    persona_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class A2AEnvelopedRequest:
    correlation_id: str
    message_id: str
    chat_hash: str
    user_hash: str
    persona_tag: str
    duty_status: str
    received_at: datetime
    prompt_checksum: str
    telemetry: dict[str, Any]
    compliance_tags: dict[str, Any]
    persona_context: dict[str, Any]
    trace: dict[str, Any]
    redaction_rules: list[str]
    sanitized_text: str
    envelope_version: int = 1


class MetadataComposer:
    """Creates envelopes aligned with Feature 2 requirements."""

    def __init__(self, config: A2AConfig) -> None:
        self.config = config

    def compose(self, command: RouterCommand) -> A2AEnvelopedRequest:
        persona = self._normalize_persona(command.persona_tag)
        if persona not in self.config.allowed_persona_tags:
            raise ConfigError(f"Persona {persona} is not allowed")
        checksum = hashlib.sha256(command.sanitized_text.encode("utf-8")).hexdigest()
        message_id = uuid.uuid4().hex
        telemetry = {
            "source": command.telemetry.get("source", "telegram_router"),
            "version": command.telemetry.get("version", "1.0.0"),
            "environment": self.config.environment,
        }
        trace = {
            "queue_depth": command.queue_depth,
            "semaphore_slots": command.semaphore_slots,
        }
        persona_context = {
            "persona": persona,
            "duty_status": command.duty_status,
            **command.persona_context,
        }
        return A2AEnvelopedRequest(
            correlation_id=command.correlation_id,
            message_id=message_id,
            chat_hash=command.chat_hash,
            user_hash=command.user_hash,
            persona_tag=persona,
            duty_status=command.duty_status,
            received_at=command.received_at,
            prompt_checksum=checksum,
            telemetry=telemetry,
            compliance_tags=command.compliance_tags or self.config.compliance_tags or {},
            persona_context=persona_context,
            trace=trace,
            redaction_rules=list(command.redaction_rules or ["telegram-router-sanitize"]),
            sanitized_text=command.sanitized_text,
        )

    def _normalize_persona(self, persona: str) -> str:
        normalized = persona.strip().replace(" ", "")
        if not normalized:
            raise ConfigError("Persona tag missing")
        mapping = {
            "operator": "Operator",
            "oncall": "OnCall",
            "incidentcommander": "IncidentCommander",
            "automationauditor": "AutomationAuditor",
        }
        key = normalized.lower().replace("_", "")
        return mapping.get(key, persona.title())
