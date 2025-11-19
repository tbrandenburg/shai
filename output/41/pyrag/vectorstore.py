"""Vector store helpers with FAISS-inspired API."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Sequence

from .embed import BaseEmbeddingModel
from .types import Document


class VectorStoreError(RuntimeError):
    pass


class SimpleVectorStore:
    def __init__(
        self,
        embeddings: List[List[float]],
        documents: List[Document],
        persist_path: Path | None = None,
    ) -> None:
        if len(embeddings) != len(documents):
            raise VectorStoreError("Embeddings/documents mismatch")
        self._records = list(zip(embeddings, documents))
        self.persist_path = persist_path
        if persist_path:
            persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [
                {
                    "metadata": doc.metadata,
                    "page_content": doc.page_content,
                }
                for _, doc in self._records
            ]
            persist_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )

    def similarity_search_by_vector(
        self, query_vector: List[float], k: int, score_threshold: float | None = None
    ) -> List[Document]:
        scored = []
        for embedding, doc in self._records:
            score = _cosine_similarity(query_vector, embedding)
            if score_threshold is None or score >= score_threshold:
                scored.append((score, doc))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for score, doc in scored[:k]]


class SimpleRetriever:
    def __init__(
        self,
        store: SimpleVectorStore,
        embedder: BaseEmbeddingModel,
        k: int,
        score_threshold: float | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.k = k
        self.score_threshold = score_threshold

    def get_relevant_documents(self, query: str) -> List[Document]:
        query_vector = self.embedder.embed_query(query)
        return self.store.similarity_search_by_vector(
            query_vector, self.k, self.score_threshold
        )


def build_vectorstore(
    embedder: BaseEmbeddingModel,
    documents: Sequence[Document],
    persist_path: Path | None = None,
) -> SimpleVectorStore:
    embeddings = embedder.embed_documents(list(documents))
    return SimpleVectorStore(embeddings, list(documents), persist_path=persist_path)


def get_retriever(
    store: SimpleVectorStore,
    embedder: BaseEmbeddingModel,
    k: int,
    score_threshold: float | None = None,
) -> SimpleRetriever:
    return SimpleRetriever(store, embedder, k=k, score_threshold=score_threshold)


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    length = min(len(a), len(b))
    if length == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(value * value for value in a[:length]))
    norm_b = math.sqrt(sum(value * value for value in b[:length]))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
