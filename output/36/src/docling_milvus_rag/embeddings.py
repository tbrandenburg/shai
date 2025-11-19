"""Embedding service built on top of SentenceTransformers with deterministic fallback."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List

import numpy as np

try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - fallback path
    SentenceTransformer = None  # type: ignore[assignment]

from .cache import Cache, NoOpCache
from .chunker import Chunk


@dataclass
class EmbeddingBatch:
    vectors: np.ndarray
    metadata: list[dict[str, str]]


class EmbeddingService:
    """Generate embeddings for documents and queries."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        batch_size: int = 32,
        normalize: bool = True,
        cache: Cache | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize = normalize
        self.cache = cache or NoOpCache()
        self.model = None
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(model_name, device=device)
            except Exception as exc:  # pragma: no cover - network restricted
                raise RuntimeError(
                    "Failed to initialize SentenceTransformer. Ensure models are available offline."
                ) from exc

    def embed_documents(self, documents: list[Chunk]) -> EmbeddingBatch:
        payload = [chunk.text for chunk in documents]
        cache_key = _hash_list(payload)
        cached = self.cache.read(cache_key)
        if cached is not None:
            vectors = np.array(cached, dtype=np.float32)
        else:
            vectors = self._embed(payload)
            self.cache.write(cache_key, vectors.tolist())
        return EmbeddingBatch(vectors=vectors, metadata=[c.metadata for c in documents])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0].tolist()

    def _embed(self, texts: list[str]) -> np.ndarray:
        if self.model is not None:
            vectors = self.model.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=self.normalize,
            )
            return vectors.astype(np.float32)
        # Deterministic hashing fallback so pipeline can still execute
        hashed = np.vstack([_hash_to_vector(text) for text in texts]).astype(np.float32)
        if self.normalize:
            norms = np.linalg.norm(hashed, axis=1, keepdims=True) + 1e-9
            hashed = hashed / norms
        return hashed


def _hash_list(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def _hash_to_vector(value: str, dim: int = 384) -> np.ndarray:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    expanded = (digest * (dim // len(digest) + 1))[:dim]
    return np.frombuffer(expanded, dtype=np.uint8).astype(np.float32)
