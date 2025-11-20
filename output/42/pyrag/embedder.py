"""Sentence-transformer embedder with deterministic fallback."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol

from pyrag.chunker import Chunk
from pyrag.config import PipelineSettings
from pyrag.exceptions import EmbedderError
from pyrag.logging import get_logger, safe_extra

logger = get_logger(__name__)

try:  # pragma: no cover - optional heavy dependency
    _hf_module = import_module("langchain_huggingface")
    HuggingFaceEmbeddings = getattr(_hf_module, "HuggingFaceEmbeddings", None)
except Exception:  # pragma: no cover - graceful fallback
    HuggingFaceEmbeddings = None  # type: ignore[assignment]


@dataclass(slots=True)
class Embedding:
    """Embedding vector paired with metadata."""

    id: str
    vector: list[float]
    metadata: dict[str, Any]


class EmbedderProtocol(Protocol):
    def embed(self, chunks: Iterable[Chunk], settings: PipelineSettings) -> list[Embedding]:
        """Return embeddings for each chunk."""

        ...

    def embed_query(self, text: str, settings: PipelineSettings) -> Embedding:
        """Return an embedding for an arbitrary text query."""

        ...

    def model_name(self, settings: PipelineSettings) -> str: ...

    def huggingface_client(self) -> Any | None: ...

    @property
    def using_fallback(self) -> bool:  # pragma: no cover - protocol hint
        ...

        ...


class HuggingFaceEmbedder(EmbedderProtocol):
    """Wraps `HuggingFaceEmbeddings` with hash fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name
        self._client: Any | None = None
        self._using_fallback = False

    def embed(self, chunks: Iterable[Chunk], settings: PipelineSettings) -> list[Embedding]:
        chunk_list = list(chunks)
        if not chunk_list:
            raise EmbedderError("No chunks supplied for embedding.")

        payloads = [chunk.text for chunk in chunk_list]
        vectors = self._vectorize(payloads, settings, is_query=False)
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
                        "strategy": "hash" if self._using_fallback else "huggingface",
                        "model": self.model_name(settings),
                        "chunk_text": chunk.text,
                    },
                )
            )
        logger.info(
            "Embedded chunks",
            extra=safe_extra(
                {
                    "count": len(embeddings),
                    "model": self.model_name(settings),
                    "strategy": "hash" if self._using_fallback else "huggingface",
                }
            ),
        )
        return embeddings

    def embed_query(self, text: str, settings: PipelineSettings) -> Embedding:
        vector = self._vectorize([text], settings, is_query=True)[0]
        metadata = {
            "chunk_id": "query",
            "strategy": "hash" if self._using_fallback else "huggingface",
            "model": self.model_name(settings),
        }
        return Embedding(id="query", vector=vector, metadata=metadata)

    def model_name(self, settings: PipelineSettings) -> str:
        return self._model_name or settings.hf_embedding_model

    def huggingface_client(self) -> Any | None:
        return self._client

    @property
    def using_fallback(self) -> bool:
        return self._using_fallback

    def _ensure_model(self, settings: PipelineSettings) -> Any:
        """Compatibility hook used by tests to disable the heavy model."""

        return self._ensure_client(settings)

    def _vectorize(
        self, payloads: list[str], settings: PipelineSettings, *, is_query: bool
    ) -> list[list[float]]:
        start = time.perf_counter()
        client = self._ensure_model(settings)
        if client is None:
            self._using_fallback = True
            vectors = [_hash_embedding(item) for item in payloads]
        else:
            try:
                if is_query:
                    vectors = [list(map(float, client.embed_query(payloads[0])))]
                else:
                    vectors = [list(map(float, row)) for row in client.embed_documents(payloads)]
                self._using_fallback = False
            except Exception as exc:  # pragma: no cover - remote failure
                logger.warning(
                    "HuggingFace embeddings unavailable; falling back to hash",
                    extra=safe_extra({"error": str(exc)}),
                )
                self._using_fallback = True
                vectors = [_hash_embedding(item) for item in payloads]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.debug(
            "Vectorized payloads",
            extra=safe_extra({"count": len(payloads), "elapsed_ms": elapsed_ms, "query": is_query}),
        )
        return vectors

    def _ensure_client(self, settings: PipelineSettings) -> Any:
        if self._client is not None:
            return self._client
        if HuggingFaceEmbeddings is None:
            return None
        try:  # pragma: no cover - heavy dependency
            self._client = HuggingFaceEmbeddings(
                model_name=self.model_name(settings),
                cache_folder=str(settings.doc_cache_dir),
                model_kwargs={"device": "cpu"},
            )
            return self._client
        except Exception as exc:  # pragma: no cover - dependency missing
            logger.warning(
                "Unable to load HuggingFaceEmbeddings; falling back to hash",
                extra=safe_extra({"error": str(exc)}),
            )
            self._client = None
            return None


MiniLMEmbedder = HuggingFaceEmbedder


def _hash_embedding(payload: str, dimensions: int = 8) -> list[float]:
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    step = max(len(digest) // dimensions, 1)
    vector: list[float] = []
    for index in range(dimensions):
        start = (index * step) % len(digest)
        chunk = digest[start : start + step]
        vector.append(int.from_bytes(chunk, "big", signed=False) / 1_000_000_000)
    return vector
