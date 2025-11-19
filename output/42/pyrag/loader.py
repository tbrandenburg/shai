"""Docling-oriented loader with deterministic offline fallback."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from pyrag.config import PipelineSettings
from pyrag.exceptions import LoaderError
from pyrag.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class DocChunk:
    """Docling-emitted chunk with provenance metadata."""

    id: str
    text: str
    metadata: dict[str, str]
    tokens: int


class LoaderProtocol(Protocol):
    """Interface for loader implementations."""

    def load(self, settings: PipelineSettings) -> list[DocChunk]:
        """Return Docling-native chunks for downstream processing."""


class DoclingLoader(LoaderProtocol):
    """Loads the Docling Technical Report while caching artifacts locally."""

    def __init__(self) -> None:
        self._cache_file = "docling_source.json"

    def load(self, settings: PipelineSettings) -> list[DocChunk]:
        start = time.perf_counter()
        try:
            payload = self._materialize_payload(settings)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Docling payload unavailable; falling back to deterministic stub",
                extra={"error": str(exc)},
            )
            payload = self._fallback_payload(settings)

        if not payload:
            raise LoaderError("Loader produced no documents; verify SOURCE_URL and DOC_CACHE_DIR.")

        doc_chunks = [
            self._to_doc_chunk(index, block, settings) for index, block in enumerate(payload)
        ]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Loaded Docling payload",
            extra={
                "doc_count": len(doc_chunks),
                "elapsed_ms": elapsed_ms,
                "cache_dir": str(settings.doc_cache_dir),
            },
        )
        return doc_chunks

    def _materialize_payload(self, settings: PipelineSettings) -> list[dict[str, str]]:
        cache_path = settings.doc_cache_dir / self._cache_file
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        # Placeholder: actual Docling export integration can drop JSON chunks here.
        payload = self._fallback_payload(settings)
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def _fallback_payload(self, settings: PipelineSettings) -> list[dict[str, str]]:
        text = (
            "Docling Technical Report placeholder for source "
            f"{settings.source_url}. This deterministic stub models loader output "
            "so the downstream chunker, embedder, and search stages can run without network access."
        )
        return [
            {
                "text": text,
                "section": "introduction",
                "page": "1",
                "checksum": "placeholder",
                "source_url": settings.source_url,
            }
        ]

    def _to_doc_chunk(
        self, index: int, block: dict[str, str], settings: PipelineSettings
    ) -> DocChunk:
        text = block.get("text", "").strip()
        if not text:
            raise LoaderError("Encountered empty Docling chunk; check export_type configuration.")
        metadata = {
            "page": block.get("page", "unknown"),
            "section": block.get("section", "unknown"),
            "checksum": block.get("checksum", "n/a"),
            "source_url": block.get("source_url", settings.source_url),
        }
        return DocChunk(
            id=f"doc-{index}",
            text=text,
            metadata=metadata,
            tokens=_estimate_tokens(text),
        )


def _estimate_tokens(text: str) -> int:
    return max(len(text.split()), 1)
