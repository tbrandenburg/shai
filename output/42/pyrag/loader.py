"""Docling-oriented loader with deterministic offline fallback."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol

from tenacity import retry, stop_after_attempt, wait_exponential

from pyrag.config import ExportType, PipelineSettings
from pyrag.exceptions import LoaderError
from pyrag.logging import get_logger, safe_extra

logger = get_logger(__name__)

try:  # pragma: no cover - optional heavy dependency
    _docling_loader_module = import_module("langchain_docling.loader")
    LCDoclingLoader = getattr(_docling_loader_module, "DoclingLoader", None)
    LCDoclingExportType = getattr(_docling_loader_module, "ExportType", None)
except Exception:  # pragma: no cover - import best-effort
    LCDoclingLoader = None  # type: ignore[assignment]
    LCDoclingExportType = None  # type: ignore[assignment]


@dataclass(slots=True)
class DocChunk:
    """Docling-emitted chunk with provenance metadata."""

    id: str
    text: str
    metadata: dict[str, Any]
    tokens: int
    strategy: str = "docling"
    docling_meta: dict[str, Any] | None = None


class LoaderProtocol(Protocol):
    """Interface for loader implementations."""

    def load(self, settings: PipelineSettings) -> list[DocChunk]:
        """Return Docling-native chunks for downstream processing."""

        ...


class DoclingLoader(LoaderProtocol):
    """Loads and caches Docling exports with retry + fallback paths."""

    def __init__(
        self,
        *,
        source_url: str | None = None,
        export_type: ExportType | None = None,
    ) -> None:
        self._source_url = source_url
        self._export_type = export_type or ExportType.DOC_CHUNKS

    def load(self, settings: PipelineSettings) -> list[DocChunk]:
        start = time.perf_counter()
        metadata: dict[str, Any]
        try:
            payload, metadata = self._materialize_payload(settings)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Docling payload unavailable; falling back to deterministic stub",
                extra=safe_extra({"error": str(exc)}),
            )
            payload, metadata = self._fallback_payload(settings, error=str(exc))
            try:
                self._write_cache(settings.docling_source_path, payload, metadata)
            except Exception as cache_exc:  # pragma: no cover - cache best effort
                logger.debug(
                    "Unable to persist fallback cache", extra=safe_extra({"error": str(cache_exc)})
                )
            metadata.setdefault("cache_hit", False)

        if not payload:
            raise LoaderError("Loader produced no documents; verify SOURCE_URL and DOC_CACHE_DIR.")

        doc_chunks = [
            self._to_doc_chunk(index, record, settings) for index, record in enumerate(payload)
        ]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        metrics = {
            "doc_count": len(doc_chunks),
            "elapsed_ms": elapsed_ms,
            **metadata,
        }
        logger.info("Loaded Docling payload", extra=safe_extra(metrics))
        return doc_chunks

    def _materialize_payload(
        self, settings: PipelineSettings
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        cache_path = settings.docling_source_path
        if cache_path.exists():
            payload, meta = self._read_cache(cache_path)
            meta.setdefault("cache_hit", True)
            meta["strategy"] = meta.get("strategy", "cache")
            return payload, meta

        payload, meta = self._download_via_docling(settings)
        self._write_cache(cache_path, payload, meta)
        meta["cache_hit"] = False
        return payload, meta

    def _read_cache(self, cache_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        content = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(content, dict) and "payload" in content:
            return list(content.get("payload", [])), dict(content.get("metadata", {}))
        return list(content), {}

    def _write_cache(
        self, cache_path: Path, payload: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> None:
        cache_path.write_text(
            json.dumps({"payload": payload, "metadata": metadata}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _download_via_docling(
        self, settings: PipelineSettings
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if LCDoclingLoader is None or LCDoclingExportType is None:
            raise LoaderError("langchain_docling is not installed in this environment")

        export_type = self._resolve_export_type(settings)
        loader = LCDoclingLoader(
            file_path=[self._source_url or settings.docling_source_url],
            export_type=export_type,
        )
        documents = self._retry_load(loader)
        payload: list[dict[str, Any]] = []
        for document in documents:
            payload.append(
                {
                    "text": document.page_content,
                    "metadata": dict(document.metadata),
                    "docling_meta": document.metadata.get("dl_meta"),
                }
            )
        meta = {
            "docling_version": getattr(loader, "__version__", ""),
            "strategy": "docling",
            "source_url": self._source_url or settings.docling_source_url,
        }
        return payload, meta

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _retry_load(self, loader: Any) -> list[Any]:  # pragma: no cover - heavy dependency
        return list(loader.load())  # type: ignore[no-any-return]

    def _fallback_payload(
        self, settings: PipelineSettings, *, error: str | None = None
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        text = (
            "Docling Technical Report placeholder for source "
            f"{settings.source_url}. This deterministic stub models loader output "
            "so the downstream chunker, embedder, and search stages can run without network access."
        )
        payload = [
            {
                "text": text,
                "metadata": {
                    "section": "introduction",
                    "page": "1",
                    "checksum": "placeholder",
                    "source_url": settings.source_url,
                },
            }
        ]
        meta = {
            "docling_version": "fallback",
            "strategy": "fallback",
        }
        if error:
            meta["error"] = error
        return payload, meta

    def _to_doc_chunk(
        self, index: int, block: dict[str, Any], settings: PipelineSettings
    ) -> DocChunk:
        text = str(block.get("text", "")).strip()
        if not text:
            raise LoaderError("Encountered empty Docling chunk; check export_type configuration.")
        metadata = dict(block.get("metadata", {}))
        metadata.setdefault("page", "unknown")
        metadata.setdefault("section", "unknown")
        metadata.setdefault("source_url", settings.source_url)
        metadata.setdefault("strategy", block.get("strategy", "docling"))
        return DocChunk(
            id=f"doc-{index}",
            text=text,
            metadata=metadata,
            tokens=_estimate_tokens(text),
            strategy=metadata["strategy"],
            docling_meta=block.get("docling_meta"),
        )

    def _resolve_export_type(
        self, settings: PipelineSettings
    ) -> Any:  # pragma: no cover - glue code
        export = self._export_type or settings.docling_export_type
        if LCDoclingExportType is None:
            return export.value
        if export == ExportType.MARKDOWN:
            return LCDoclingExportType.MARKDOWN
        return LCDoclingExportType.DOC_CHUNKS


def _estimate_tokens(text: str) -> int:
    return max(len(text.split()), 1)
