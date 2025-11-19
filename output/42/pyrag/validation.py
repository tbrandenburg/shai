"""Validation helpers for end-to-end RAG execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyrag.exceptions import ValidationError
from pyrag.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from pyrag.pipeline import RunSummary

logger = get_logger(__name__)

REQUIRED_THRESHOLDS = {
    "documents": 1,
    "chunks": 1,
    "embeddings": 1,
    "hits": 1,
}


def validate(summary: RunSummary) -> dict[str, int]:
    """Validate the run summary and return aggregate counts for telemetry."""

    counts = {
        "documents": len(summary.documents),
        "chunks": len(summary.chunks),
        "embeddings": len(summary.embeddings),
        "hits": len(summary.search_result.sources),
    }
    for key, minimum in REQUIRED_THRESHOLDS.items():
        if counts[key] < minimum:
            raise ValidationError(f"Validation failed: {key} below minimum {minimum}.")
    logger.info("Validation passed for collection %s", summary.search_result.top_k)
    return counts
