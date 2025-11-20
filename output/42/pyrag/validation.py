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

    validation_enabled = bool(summary.settings_snapshot.get("validation_enabled", True))
    if validation_enabled:
        loader_strategy = summary.metrics.get("loader", {}).get("strategy")
        if loader_strategy == "fallback":
            raise ValidationError("Loader fallback not permitted when validation is enabled.")
        embedder_strategy = summary.metrics.get("embedder", {}).get("strategy")
        if embedder_strategy and embedder_strategy != "huggingface":
            raise ValidationError("Embedder must use HuggingFace strategy during validation runs.")
        if summary.search_result.fallback_used:
            raise ValidationError(
                "LLM fallback triggered; rerun with a reachable HuggingFaceEndpoint."
            )
    logger.info("Validation passed for retrieval depth %s", summary.search_result.top_k)
    return counts
