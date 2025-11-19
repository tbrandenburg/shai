"""Search orchestration built on the embedder + storage modules."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from pyrag.config import PipelineSettings
from pyrag.embedder import EmbedderProtocol, Embedding
from pyrag.exceptions import SearchError
from pyrag.logging import get_logger
from pyrag.storage import StorageHandle, StorageProtocol

logger = get_logger(__name__)


@dataclass(slots=True)
class RetrievedSource:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, str]


@dataclass(slots=True)
class SearchResult:
    question: str
    answer: str
    sources: list[RetrievedSource]
    latency_ms: float
    top_k: int
    confidence_scores: list[float]


class SearchOrchestrator:
    def ask(
        self, handle: StorageHandle, query_text: str, settings: PipelineSettings
    ) -> SearchResult:
        raise NotImplementedError


class LangChainSearch(SearchOrchestrator):
    """Placeholder for LangChain retriever/LLM logic (deterministic summary for now)."""

    def __init__(self, store: StorageProtocol, embedder: EmbedderProtocol) -> None:
        self._store = store
        self._embedder = embedder

    def ask(
        self, handle: StorageHandle, query_text: str, settings: PipelineSettings
    ) -> SearchResult:
        start = time.perf_counter()
        query_embedding = self._embedder.embed_query(query_text, settings)
        ranked = self._store.query(query_embedding.vector, settings.top_k)
        if not ranked:
            raise SearchError(
                "Search returned no hits; try increasing TOP_K or verifying the loader output."
            )

        sources = [
            RetrievedSource(
                chunk_id=embedding.metadata.get("chunk_id", embedding.id),
                score=score,
                text=embedding.metadata.get("chunk_text") or embedding.metadata.get("snippet", ""),
                metadata=embedding.metadata,
            )
            for embedding, score in ranked
        ]

        answer = self._summarize(ranked, query_text)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "Search completed",
            extra={
                "latency_ms": latency_ms,
                "top_k": settings.top_k,
                "collection": handle.collection_name,
            },
        )
        return SearchResult(
            question=query_text,
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
            top_k=settings.top_k,
            confidence_scores=[score for _, score in ranked],
        )

    def _summarize(self, ranked: list[tuple[Embedding, float]], query_text: str) -> str:
        snippets = [
            (embedding.metadata.get("snippet") or embedding.metadata.get("chunk_id", ""))
            for embedding, _ in ranked
        ]
        confidence = statistics.mean(score for _, score in ranked)
        return (
            f"Retrieved {len(ranked)} chunks for '{query_text}'. "
            f"Mean confidence {confidence:.2f}. Sources: {', '.join(snippets)}"
        )
