"""Milvus-inspired storage abstraction with in-memory fallback."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Protocol

from pyrag.config import PipelineSettings
from pyrag.embedder import EmbedderProtocol, Embedding
from pyrag.exceptions import StorageError
from pyrag.logging import get_logger, redact_uri, safe_extra

logger = get_logger(__name__)

try:  # pragma: no cover - optional dependency
    _milvus_module = import_module("langchain_milvus")
    LangChainMilvus = getattr(_milvus_module, "Milvus", None)
except Exception:  # pragma: no cover - graceful fallback
    LangChainMilvus = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    _lc_documents = import_module("langchain_core.documents")
    LCDocument = getattr(_lc_documents, "Document", None)
except Exception:  # pragma: no cover - fallback shim
    LCDocument = None  # type: ignore[assignment]


@dataclass(slots=True)
class StorageHandle:
    """Represents a persisted embedding collection."""

    collection_name: str
    dimension: int
    milvus_uri: str
    teardown: Callable[[], None]
    metadata: dict[str, Any] = field(default_factory=dict)
    vectorstore: Any | None = None


class StorageProtocol(Protocol):
    def persist(
        self,
        embeddings: Iterable[Embedding],
        collection: str,
        *,
        settings: PipelineSettings,
        embedder: EmbedderProtocol,
    ) -> StorageHandle:
        """Insert embeddings into the backing store and return a handle."""

        raise NotImplementedError

    def query(self, query_vector: list[float], top_k: int) -> list[tuple[Embedding, float]]:
        """Return embeddings ranked by similarity along with their scores."""

        raise NotImplementedError


class MilvusStore(StorageProtocol):
    """Adapter that prefers Milvus but falls back to deterministic in-memory vectors."""

    def __init__(self, uri: str | None = None, settings: PipelineSettings | None = None) -> None:
        self._settings = settings
        self._uri = (uri or (settings.milvus_uri if settings else "")) or "milvus-lite://memory"
        self._rows: list[Embedding] = []
        self._vectorstore: Any | None = None
        self._embedder: EmbedderProtocol | None = None
        self._mode = "lite" if self._uri.startswith("file://") else "remote"

    def persist(
        self,
        embeddings: Iterable[Embedding],
        collection: str,
        *,
        settings: PipelineSettings,
        embedder: EmbedderProtocol,
    ) -> StorageHandle:
        rows = list(embeddings)
        if not rows:
            raise StorageError("No embeddings supplied to storage.")
        self._rows = rows
        self._settings = settings
        self._embedder = embedder

        self._vectorstore, status = self._initialize_vectorstore(collection)
        dimension = len(rows[0].vector)
        metadata = {
            "insert_count": len(rows),
            "collection": collection,
            "dimension": dimension,
            "mode": self._mode,
            "status": status,
        }
        logger.info(
            "Persisted embeddings",
            extra=safe_extra({"collection": collection, "count": len(rows), "status": status}),
        )
        return StorageHandle(
            collection_name=collection,
            dimension=dimension,
            milvus_uri=self._uri,
            teardown=self._teardown_vectorstore,
            metadata=metadata,
            vectorstore=self._vectorstore,
        )

    def query(self, query_vector: list[float], top_k: int) -> list[tuple[Embedding, float]]:
        if not self._rows:
            raise StorageError("Storage is empty; ensure persist() ran before query().")
        scores = [(row, _cosine_similarity(row.vector, query_vector)) for row in self._rows]
        ranked = sorted(scores, key=lambda item: item[1], reverse=True)
        return ranked[:top_k]

    def _initialize_vectorstore(self, collection: str) -> tuple[Any, str]:
        docs = [_to_document(row) for row in self._rows]
        if LangChainMilvus is not None and self._mode != "lite" and self._settings:
            embedding_client = getattr(self._embedder, "huggingface_client", lambda: None)()
            if embedding_client is not None:
                try:  # pragma: no cover - depends on actual Milvus service
                    vectorstore = LangChainMilvus.from_documents(
                        documents=docs,
                        embedding=embedding_client,
                        connection_args={"uri": self._uri},
                        collection_name=collection,
                    )
                    return vectorstore, "milvus"
                except Exception as exc:
                    logger.warning(
                        "Milvus connection failed; using in-memory fallback",
                        extra=safe_extra({"error": str(exc), "uri": redact_uri(self._uri)}),
                    )
        fallback = _LiteVectorStore(self._rows, self._embedder, self._settings)
        return fallback, "lite" if self._mode == "lite" else "fallback"

    def _teardown_vectorstore(self) -> None:
        self._rows.clear()
        self._vectorstore = None


def _to_document(row: Embedding) -> Any:
    metadata = dict(row.metadata)
    metadata.setdefault("chunk_id", row.id)
    text = metadata.get("chunk_text", metadata.get("snippet", ""))
    if LCDocument is not None:  # pragma: no cover - depends on LangChain
        return LCDocument(page_content=text, metadata=metadata)
    return {"page_content": text, "metadata": metadata}


class _LiteVectorStore:
    """Minimal vector store compatible with LangChain retrievers."""

    def __init__(
        self,
        rows: list[Embedding],
        embedder: EmbedderProtocol | None,
        settings: PipelineSettings | None,
    ) -> None:
        self._rows = rows
        self._embedder = embedder
        self._settings = settings

    def as_retriever(self, search_kwargs: dict[str, Any] | None = None) -> _LiteRetriever:
        kwargs = search_kwargs or {}
        top_k = int(kwargs.get("k", 4))
        return _LiteRetriever(self._rows, self._embedder, self._settings, top_k)

    def similarity_search_with_score_by_vector(
        self, query_vector: list[float], k: int
    ) -> list[tuple[Any, float]]:
        ranked = sorted(
            ((row, _cosine_similarity(row.vector, query_vector)) for row in self._rows),
            key=lambda item: item[1],
            reverse=True,
        )
        docs = [(_to_document(row), score) for row, score in ranked[:k]]
        return docs


class _LiteRetriever:
    def __init__(
        self,
        rows: list[Embedding],
        embedder: EmbedderProtocol | None,
        settings: PipelineSettings | None,
        top_k: int,
    ) -> None:
        self._rows = rows
        self._embedder = embedder
        self._settings = settings
        self._top_k = top_k

    def invoke(self, query: str) -> list[Any]:
        return self.get_relevant_documents(query)

    def get_relevant_documents(self, query: str) -> list[Any]:
        return self._collect_documents(query)

    def _collect_documents(
        self, query: str
    ) -> list[Any]:  # pragma: no cover - exercised via search
        if not self._embedder or not self._settings:
            raise StorageError("Embedder unavailable for fallback retriever.")
        query_embedding = self._embedder.embed_query(query, self._settings)
        ranked = sorted(
            ((row, _cosine_similarity(row.vector, query_embedding.vector)) for row in self._rows),
            key=lambda item: item[1],
            reverse=True,
        )
        documents = [_to_document(row) for row, _ in ranked[: self._top_k]]
        return documents


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
