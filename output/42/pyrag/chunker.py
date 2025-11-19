"""Chunker implementations that normalize Docling outputs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from pyrag.config import PipelineSettings
from pyrag.exceptions import ChunkerError
from pyrag.loader import DocChunk
from pyrag.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Chunk:
    """Normalized chunk used by the embedder."""

    id: str
    text: str
    metadata: dict[str, str]
    order_index: int


class ChunkerProtocol(Protocol):
    def split(self, documents: Iterable[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        """Split Docling outputs into deterministic downstream chunks."""


class HybridChunker(ChunkerProtocol):
    """Combines Docling structural chunks with fallback recursive splitting."""

    def split(self, documents: Iterable[DocChunk], settings: PipelineSettings) -> list[Chunk]:
        docs = list(documents)
        if not docs:
            raise ChunkerError("No documents provided to chunker.")

        chunks: list[Chunk] = []
        overlap = settings.chunk_overlap
        chunk_size = settings.chunk_size
        step = max(chunk_size - overlap, 1)
        for doc_index, document in enumerate(docs):
            text = document.text.strip()
            if not text:
                continue
            mode = "DOC_CHUNKS" if len(text) <= chunk_size else "HYBRID"
            for start in range(0, len(text), step):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                order_index = len(chunks)
                metadata = {
                    **document.metadata,
                    "doc_id": document.id,
                    "chunk_mode": mode,
                    "token_estimate": str(max(len(chunk_text.split()), 1)),
                    "offset": str(start),
                }
                chunk = Chunk(
                    id=f"{document.id}:{doc_index}:{order_index}",
                    text=chunk_text,
                    metadata=metadata,
                    order_index=order_index,
                )
                chunks.append(chunk)

        if not chunks:
            raise ChunkerError("Chunker produced zero output; check chunk size configuration.")
        logger.info("Chunked %s documents into %s chunks", len(docs), len(chunks))
        return chunks
