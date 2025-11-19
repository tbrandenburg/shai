"""Pipeline orchestration across loader, chunker, embedder, storage, and search."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from pyrag.chunker import Chunk, ChunkerProtocol, HybridChunker
from pyrag.config import PipelineSettings
from pyrag.embedder import EmbedderProtocol, Embedding, MiniLMEmbedder
from pyrag.loader import DocChunk, DoclingLoader, LoaderProtocol
from pyrag.logging import get_logger
from pyrag.search import LangChainSearch, SearchOrchestrator, SearchResult
from pyrag.storage import MilvusStore, StorageProtocol

logger = get_logger(__name__)


@dataclass(slots=True)
class RunSummary:
    documents: list[DocChunk]
    chunks: list[Chunk]
    embeddings: list[Embedding]
    search_result: SearchResult
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    settings_snapshot: dict[str, str] = field(default_factory=dict)


class RunnerProtocol(Protocol):
    def run(self, settings: PipelineSettings) -> RunSummary: ...


class PipelineRunner(RunnerProtocol):
    """Coordinates the modular RAG pipeline."""

    def __init__(
        self,
        loader: LoaderProtocol | None = None,
        chunker: ChunkerProtocol | None = None,
        embedder: EmbedderProtocol | None = None,
        storage: StorageProtocol | None = None,
        search: SearchOrchestrator | None = None,
    ) -> None:
        self.loader = loader or DoclingLoader()
        self.chunker = chunker or HybridChunker()
        self.embedder = embedder or MiniLMEmbedder()
        self.storage = storage or MilvusStore()
        self.search = search or LangChainSearch(self.storage, self.embedder)

    def run(self, settings: PipelineSettings) -> RunSummary:
        settings.ensure_valid()
        metrics: dict[str, dict[str, Any]] = {}
        with ExitStack() as stack:
            documents = self._capture_stage(
                "loader",
                metrics,
                lambda: self.loader.load(settings),
                count=lambda docs: len(docs),
            )
            chunks = self._capture_stage(
                "chunker",
                metrics,
                lambda: self.chunker.split(documents, settings),
                count=lambda rows: len(rows),
            )
            embeddings = self._capture_stage(
                "embedder",
                metrics,
                lambda: self.embedder.embed(chunks, settings),
                count=lambda rows: len(rows),
            )
            storage_handle = self._capture_stage(
                "storage",
                metrics,
                lambda: self.storage.persist(embeddings, settings.milvus_collection),
                count=lambda handle: int(handle.metadata.get("insert_count", "0")),
                enrich=lambda handle: {
                    "collection": handle.collection_name,
                    "milvus_uri": handle.milvus_uri,
                },
            )
            stack.callback(storage_handle.teardown)
            search_result = self._capture_stage(
                "search",
                metrics,
                lambda: self.search.ask(storage_handle, settings.query_text, settings),
                count=lambda result: len(result.sources),
                enrich=lambda result: {"question": result.question},
            )
        summary = RunSummary(
            documents=documents,
            chunks=chunks,
            embeddings=embeddings,
            search_result=search_result,
            metrics=metrics,
            settings_snapshot=settings.snapshot(),
        )
        logger.info(
            "Pipeline finished",
            extra={
                "documents": len(documents),
                "chunks": len(chunks),
                "embeddings": len(embeddings),
                "hits": len(search_result.sources),
            },
        )
        return summary

    def _capture_stage(
        self,
        name: str,
        metrics: dict[str, dict[str, Any]],
        producer: Callable[[], Any],
        *,
        count: Callable[[Any], int],
        enrich: Callable[[Any], dict[str, Any]] | None = None,
    ) -> Any:
        start = perf_counter()
        result = producer()
        elapsed_ms = round((perf_counter() - start) * 1000, 2)
        metadata = {"elapsed_ms": elapsed_ms, "count": count(result)}
        if enrich is not None:
            metadata.update(enrich(result))
        metrics[name] = metadata
        return result
