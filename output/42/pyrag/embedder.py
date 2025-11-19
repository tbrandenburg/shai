"""Sentence-transformer embedder with deterministic fallback."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from pyrag.chunker import Chunk
from pyrag.config import PipelineSettings
from pyrag.exceptions import EmbedderError
from pyrag.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Embedding:
    """Embedding vector paired with metadata."""

    id: str
    vector: list[float]
    metadata: dict[str, str]


class EmbedderProtocol(Protocol):
    def embed(self, chunks: Iterable[Chunk], settings: PipelineSettings) -> list[Embedding]:
        """Return embeddings for each chunk."""

    def embed_query(self, text: str, settings: PipelineSettings) -> Embedding:
        """Return an embedding for an arbitrary text query."""


class MiniLMEmbedder(EmbedderProtocol):
    """Wraps `sentence-transformers/all-MiniLM-L6-v2` with hash fallback."""

    def __init__(self) -> None:
        self._model = None

    def embed(self, chunks: Iterable[Chunk], settings: PipelineSettings) -> list[Embedding]:
        chunk_list = list(chunks)
        if not chunk_list:
            raise EmbedderError("No chunks supplied for embedding.")

        vectors = self._encode([chunk.text for chunk in chunk_list], settings)
        embeddings: list[Embedding] = []
        for order_index, (chunk, vector) in enumerate(zip(chunk_list, vectors, strict=True)):
            embeddings.append(
                Embedding(
                    id=f"embed-{order_index}",
                    vector=vector,
                    metadata={
                        "chunk_id": chunk.id,
                        "order_index": str(order_index),
                        "snippet": chunk.text[:160],
                        "chunk_text": chunk.text,
                    },
                )
            )
        logger.info("Embedded %s chunks", len(embeddings))
        return embeddings

    def embed_query(self, text: str, settings: PipelineSettings) -> Embedding:
        vector = self._encode([text], settings)[0]
        return Embedding(id="query", vector=vector, metadata={"chunk_id": "query"})

    def _encode(self, payloads: list[str], settings: PipelineSettings) -> list[list[float]]:
        start = time.perf_counter()
        model = self._ensure_model(settings)
        if model is None:
            logger.info("Using hash-based embedding fallback")
            vectors = [_hash_embedding(item) for item in payloads]
        else:
            vectors = [
                list(map(float, row)) for row in model.encode(payloads, show_progress_bar=False)
            ]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("Encoded %s payloads in %s ms", len(payloads), elapsed_ms)
        return vectors

    def _ensure_model(self, settings: PipelineSettings):  # type: ignore[no-untyped-def]
        if self._model is not None:
            return self._model
        try:  # pragma: no cover - optional heavy dependency
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
                use_auth_token=settings.hf_token,
            )
            logger.info(
                "Loaded sentence-transformers MiniLM model (auth token %s)",
                "set" if settings.hf_token else "not set",
            )
        except Exception as exc:
            logger.warning(
                "SentenceTransformer unavailable (%s); falling back to hash embeddings", exc
            )
            self._model = None
        return self._model


def _hash_embedding(payload: str, dimensions: int = 8) -> list[float]:
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    step = max(len(digest) // dimensions, 1)
    vector: list[float] = []
    for index in range(dimensions):
        start = (index * step) % len(digest)
        chunk = digest[start : start + step]
        vector.append(int.from_bytes(chunk, "big", signed=False) / 1_000_000_000)
    return vector
