"""Milvus-backed vector store with in-memory fallback for offline execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List

import numpy as np

from .config import MilvusConfig
from .embeddings import EmbeddingBatch

try:  # pragma: no cover - optional dependency
    from pymilvus import MilvusClient
except Exception:  # pragma: no cover - fallback path
    MilvusClient = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, str]


class MilvusStore:
    """Insert and query embeddings via Milvus Lite or memory fallback."""

    def __init__(self, cfg: MilvusConfig, dim: int = 384) -> None:
        self.cfg = cfg
        self.dim = dim
        self._memory_vectors: list[np.ndarray] = []
        self._memory_metadata: list[dict[str, str]] = []
        self._client = None
        if MilvusClient is not None:
            try:
                self._client = MilvusClient(uri=cfg.uri)
                if cfg.drop_existing:
                    self._client.drop_collection(cfg.collection_name)
                if not self._client.has_collection(cfg.collection_name):
                    self._client.create_collection(
                        collection_name=cfg.collection_name,
                        dimension=dim,
                        metric_type="COSINE",
                    )
            except Exception as exc:  # pragma: no cover - ensure fallback works
                LOGGER.warning("Milvus Lite unavailable, using in-memory store", exc_info=exc)
                self._client = None

    def upsert(self, batch: EmbeddingBatch) -> int:
        if self._client is not None:
            records = [
                {
                    "vector": vector.tolist(),
                    "doc_id": meta.get("doc_id", ""),
                    "payload": meta,
                }
                for vector, meta in zip(batch.vectors, batch.metadata, strict=False)
            ]
            self._client.insert(
                collection_name=self.cfg.collection_name,
                data=records,
            )
            return len(records)
        self._memory_vectors.extend(batch.vectors)
        self._memory_metadata.extend(batch.metadata)
        return len(batch.metadata)

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int,
        filter_doc_id: str | None = None,
    ) -> list[RetrievedChunk]:
        if self._client is not None:
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64},
            }
            qry = [query_vector]
            filter_expr = None
            if filter_doc_id:
                filter_expr = f"doc_id == '{filter_doc_id}'"
            result = self._client.search(
                collection_name=self.cfg.collection_name,
                data=qry,
                limit=top_k,
                search_params=search_params,
                filter=filter_expr,
                output_fields=["payload"],
                consistency_level=self.cfg.consistency_level,
            )
            chunks: list[RetrievedChunk] = []
            for hit in result[0]:
                payload = hit.get("payload", {})
                chunks.append(
                    RetrievedChunk(
                        text=payload.get("text", ""),
                        score=float(hit.get("distance", 0.0)),
                        metadata=payload,
                    )
                )
            return chunks
        if not self._memory_vectors:
            return []
        vectors = np.vstack(self._memory_vectors)
        query = np.array(query_vector, dtype=np.float32)
        scores = vectors @ query / (np.linalg.norm(vectors, axis=1) * (np.linalg.norm(query) + 1e-9))
        results = []
        for idx in np.argsort(scores)[::-1][:top_k]:
            meta = self._memory_metadata[int(idx)]
            if filter_doc_id and meta.get("doc_id") != filter_doc_id:
                continue
            results.append(
                RetrievedChunk(
                    text=meta.get("text", ""),
                    score=float(scores[int(idx)]),
                    metadata=meta,
                )
            )
        return results

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                LOGGER.debug("Milvus client close failed", exc_info=True)
