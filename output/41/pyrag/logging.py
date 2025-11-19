"""Structured logging helpers for pyrag."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

_STAGE_LOGGER = logging.getLogger("pyrag")


def configure_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(asctime)s %(message)s",
        handlers=handlers,
        force=True,
    )


def log_stage(stage: str, event: str, **metadata: Any) -> None:
    payload = {"stage": stage, "event": event, **metadata}
    if metadata.get("json"):
        _STAGE_LOGGER.info(json.dumps(payload, default=str))
    else:
        extras = {k: v for k, v in payload.items() if k not in {"stage", "event"}}
        _STAGE_LOGGER.info("%s %s %s", stage, event, extras if extras else "")
