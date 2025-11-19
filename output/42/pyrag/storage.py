"""Milvus-inspired storage abstraction with in-memory fallback."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

from pyrag.embedder import Embedding
from pyrag.exceptions import StorageError
from pyrag.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class StorageHandle:
    """Represents a persisted embedding collection."""

    collection_name: str
    dimension: int
    milvus_uri: str
    teardown: Callable[[], None]
    metadata: dict[str, str] = field(default_factory=dict)


class StorageProtocol(Protocol):
    def persist(self, embeddings: Iterable[Embedding], collection: str) -> StorageHandle:
        """Insert embeddings into the backing store and return a handle."""

    def query(self, query_vector: list[float], top_k: int) -> list[tuple[Embedding, float]]:
        """Return embeddings ranked by similarity along with their scores."""


class MilvusStore(StorageProtocol):
    """Simplified Milvus/Lite adapter that stores vectors in memory for now."""

    def __init__(self, uri: str | None = None) -> None:
        self._uri = uri or "milvus-lite://memory"
        self._rows: list[Embedding] = []

    def persist(self, embeddings: Iterable[Embedding], collection: str) -> StorageHandle:
        self._rows = list(embeddings)
        if not self._rows:
            raise StorageError("No embeddings supplied to storage.")
        dimension = len(self._rows[0].vector)
        logger.info("Persisted %s embeddings into %s", len(self._rows), collection)
        return StorageHandle(
            collection_name=collection,
            dimension=dimension,
            milvus_uri=self._uri,
            teardown=self._rows.clear,
            metadata={"insert_count": str(len(self._rows)), "index_type": "FLAT"},
        )

    def query(self, query_vector: list[float], top_k: int) -> list[tuple[Embedding, float]]:
        if not self._rows:
            raise StorageError("Storage is empty; ensure persist() ran before query().")
        scores = [(row, _cosine_similarity(row.vector, query_vector)) for row in self._rows]
        ranked = sorted(scores, key=lambda item: item[1], reverse=True)
        return ranked[:top_k]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
