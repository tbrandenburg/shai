"""Offline-friendly RAG helpers for the pyrag CLI."""

from __future__ import annotations

from .config import PipelineConfig, load_config
from .pipeline import execute, format_answer

__all__ = [
    "PipelineConfig",
    "load_config",
    "execute",
    "format_answer",
]

__version__ = "0.1.0"
