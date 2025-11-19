"""Document chunking utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

try:  # pragma: no cover - optional dependency
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover - fallback path
    RecursiveCharacterTextSplitter = None  # type: ignore[assignment]

from .docling_loader import RawDoc


@dataclass
class Chunk:
    text: str
    metadata: dict[str, str]


class ChunkBuilder:
    """Split raw document pages into chunked strings."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build(self, docs: Iterable[RawDoc]) -> list[Chunk]:
        if RecursiveCharacterTextSplitter is None:
            return self._fallback_chunks(docs)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        chunks: list[Chunk] = []
        for raw in docs:
            for idx, chunk in enumerate(splitter.split_text(raw.text)):
                chunks.append(
                    Chunk(
                        text=chunk,
                        metadata={
                            **raw.metadata,
                            "chunk_index": str(idx),
                            "doc_id": raw.doc_id,
                        },
                    )
                )
        return chunks

    def _fallback_chunks(self, docs: Iterable[RawDoc]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for raw in docs:
            text = raw.text
            for idx in range(0, len(text), self.chunk_size):
                chunk_text = text[idx : idx + self.chunk_size]
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        metadata={
                            **raw.metadata,
                            "chunk_index": str(len(chunks)),
                            "doc_id": raw.doc_id,
                        },
                    )
                )
        return chunks
