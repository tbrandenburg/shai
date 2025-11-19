"""Shared data structures for the pyrag pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Document:
    """Simplified stand-in for LangChain's Document."""

    page_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Represents the outcome returned by ``pipeline.execute``."""

    answer: str
    context: List[Document]
    fallback_used: bool
    diagnostics: Dict[str, Any] = field(default_factory=dict)
