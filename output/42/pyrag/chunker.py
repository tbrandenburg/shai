"""Chunker implementations that normalize Docling outputs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from pyrag.config import ExportType, PipelineSettings
from pyrag.exceptions import ChunkerError
from pyrag.loader import DocChunk
from pyrag.logging import get_logger, safe_extra

logger = get_logger(__name__)

try:  # pragma: no cover - optional dependency
    _markdown_module = import_module("langchain_text_splitters")
    MarkdownHeaderTextSplitter = getattr(_markdown_module, "MarkdownHeaderTextSplitter", None)
except Exception:  # pragma: no cover - best effort import
    MarkdownHeaderTextSplitter = None  # type: ignore[assignment]


@dataclass(slots=True)
class Chunk:
    """Normalized chunk used by the embedder."""

    id: str
    text: str
    metadata: dict[str, Any]
    order_index: int


class ChunkerProtocol(Protocol):
    def split(self, documents: Iterable[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        """Split Docling outputs into deterministic downstream chunks."""

        ...


class DoclingHybridChunker(ChunkerProtocol):
    """Combines Docling structural chunks with fallback recursive splitting."""

    def split(self, documents: Iterable[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        docs = [doc for doc in documents if doc.text.strip()]
        if not docs:
            raise ChunkerError("No documents provided to chunker.")

        if settings.export_type == ExportType.MARKDOWN or any(
            doc.strategy != "docling" for doc in docs
        ):
            chunks = self._chunk_markdown(docs, settings)
        else:
            chunks = self._chunk_doc_chunks(docs, settings)

        if not chunks:
            raise ChunkerError("Chunker produced zero output; check chunk size configuration.")

        strategy_counts = Counter(chunk.metadata.get("strategy", "unknown") for chunk in chunks)
        logger.info(
            "Chunked documents",
            extra=safe_extra(
                {
                    "document_count": len(docs),
                    "chunk_count": len(chunks),
                    "strategy_counts": dict(strategy_counts),
                    "chunk_size": settings.chunk_size,
                    "chunk_overlap": settings.chunk_overlap,
                }
            ),
        )
        return chunks

    def _chunk_doc_chunks(self, docs: list[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        overlap = settings.chunk_overlap
        chunk_size = settings.chunk_size
        step = max(chunk_size - overlap, 1)
        chunks: list[Chunk] = []
        for doc_index, document in enumerate(docs):
            strategy = document.strategy or "docling"
            text = document.text.strip()
            for offset, start in enumerate(range(0, len(text), step)):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                metadata = dict(document.metadata)
                metadata.update(
                    {
                        "doc_id": document.id,
                        "strategy": strategy,
                        "chunk_mode": "DOC_CHUNKS" if len(text) <= chunk_size else "HYBRID",
                        "offset": str(start),
                        "token_estimate": str(max(len(chunk_text.split()), 1)),
                    }
                )
                chunks.append(
                    Chunk(
                        id=f"{document.id}:{doc_index}:{offset}",
                        text=chunk_text,
                        metadata=metadata,
                        order_index=len(chunks),
                    )
                )
        return chunks

    def _chunk_markdown(self, docs: list[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        splitter = self._markdown_splitter()
        if splitter is None:
            return self._chunk_doc_chunks(docs, settings)

        chunks: list[Chunk] = []
        for doc_index, document in enumerate(docs):
            splits = splitter.split_text(document.text)
            for offset, segment in enumerate(splits):
                if hasattr(segment, "page_content"):
                    text = segment.page_content
                    meta = getattr(segment, "metadata", {}) or {}
                elif isinstance(segment, dict):
                    text = segment.get("text") or segment.get("content", "")
                    meta = segment.get("metadata", {})
                else:
                    text = str(segment)
                    meta = {}
                metadata = dict(document.metadata)
                metadata.update(meta)
                metadata.update(
                    {
                        "doc_id": document.id,
                        "strategy": "markdown",
                        "chunk_mode": "MARKDOWN",
                        "offset": str(offset),
                    }
                )
                chunks.append(
                    Chunk(
                        id=f"md-{document.id}:{doc_index}:{offset}",
                        text=text,
                        metadata=metadata,
                        order_index=len(chunks),
                    )
                )
        return chunks

    def _markdown_splitter(self) -> Any:  # pragma: no cover - optional dependency bridge
        if MarkdownHeaderTextSplitter is None:
            return None
        if not hasattr(self, "_splitter"):
            headers = [("#", "Header1"), ("##", "Header2"), ("###", "Header3")]
            self._splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
        return self._splitter


HybridChunker = DoclingHybridChunker
