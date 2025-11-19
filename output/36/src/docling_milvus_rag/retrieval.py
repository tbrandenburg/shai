"""Retriever wiring chunk embeddings with the query embedder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .embeddings import EmbeddingService
from .milvus_store import MilvusStore, RetrievedChunk


@dataclass
class RetrieverResult:
    query: str
    chunks: list[RetrievedChunk]


class Retriever:
    def __init__(
        self,
        store: MilvusStore,
        embedder: EmbeddingService,
        top_k: int = 4,
        score_threshold: float | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.score_threshold = score_threshold

    def run(self, question: str, doc_id: str | None = None) -> RetrieverResult:
        query_vector = self.embedder.embed_query(question)
        hits = self.store.similarity_search(
            query_vector=query_vector,
            top_k=self.top_k,
            filter_doc_id=doc_id,
        )
        if self.score_threshold is not None:
            hits = [hit for hit in hits if hit.score >= self.score_threshold]
        return RetrieverResult(query=question, chunks=hits)
