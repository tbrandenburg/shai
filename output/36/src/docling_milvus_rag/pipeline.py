"""Pipeline orchestration for the Docling → Milvus offline workflow."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .cache import Cache
from .chunker import ChunkBuilder
from .config import AppConfig, load_config
from .docling_loader import DoclingIngestor
from .embeddings import EmbeddingService
from .llm import AnswerGenerator, AnswerResult
from .logging import configure_logging, get_logger
from .milvus_store import MilvusStore
from .retrieval import Retriever


@dataclass
class PipelineResult:
    answer: str
    chunks_indexed: int
    metrics: dict[str, float]


class Pipeline:
    """High-level orchestrator for ingestion → retrieval → generation."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        configure_logging(
            json_logs=config.runtime.json_logs,
            level=config.runtime.log_level,
        )
        self.logger = get_logger()
        cache = Cache(config.runtime.cache_dir)
        self.ingestor = DoclingIngestor(cache=cache)
        self.chunk_builder = ChunkBuilder(
            chunk_size=config.chunk.size,
            chunk_overlap=config.chunk.overlap,
        )
        self.embedder = EmbeddingService(
            model_name=config.embeddings.model_name,
            device=config.embeddings.device,
            batch_size=config.embeddings.batch_size,
            normalize=config.embeddings.normalize_embeddings,
            cache=cache,
        )
        self.store = MilvusStore(cfg=config.milvus, dim=config.milvus.dim)
        self.retriever = Retriever(
            store=self.store,
            embedder=self.embedder,
            top_k=config.retrieval.top_k,
            score_threshold=config.retrieval.score_threshold,
        )
        self.answerer = AnswerGenerator(config.llm)

    def run(self) -> PipelineResult:
        start = time.perf_counter()
        docs = self.ingestor.ingest(self.config.pdf_paths)
        chunks = self.chunk_builder.build(docs)
        embedding_batch = self.embedder.embed_documents(chunks)
        # include chunk text inside metadata for retrieval fallbacks
        for chunk_meta, chunk in zip(embedding_batch.metadata, chunks, strict=False):
            chunk_meta.setdefault("text", chunk.text)
        inserted = self.store.upsert(embedding_batch)
        retriever_result = self.retriever.run(
            question=self.config.question,
            doc_id=chunks[0].metadata.get("doc_id") if chunks else None,
        )
        answer_result = self.answerer.generate(
            question=self.config.question,
            contexts=retriever_result.chunks,
        )
        total = time.perf_counter() - start
        metrics = {"duration_sec": total, **answer_result.metrics}
        return PipelineResult(
            answer=answer_result.answer,
            chunks_indexed=inserted,
            metrics=metrics,
        )


def run_pipeline(
    cli_args: dict | None = None,
    defaults_path: str | Path | None = None,
) -> PipelineResult:
    """Convenience helper used by CLI/tests."""

    config = load_config(cli_args, defaults_path=defaults_path)
    pipeline = Pipeline(config)
    return pipeline.run()
