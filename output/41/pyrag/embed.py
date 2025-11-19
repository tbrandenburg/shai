"""Embedding factories with offline fallbacks."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import List

from .types import Document

_LOG = logging.getLogger("pyrag.embed")
_TOKEN_PATTERN = re.compile(r"\w+")


class EmbeddingInitError(RuntimeError):
    pass


class BaseEmbeddingModel:
    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        raise NotImplementedError


class SentenceTransformerWrapper(BaseEmbeddingModel):
    def __init__(self, model_name: str, cache_dir: Path):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise EmbeddingInitError(str(exc)) from exc

        cache_dir.mkdir(parents=True, exist_ok=True)
        self._model = SentenceTransformer(model_name, cache_folder=str(cache_dir))

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        texts = [doc.page_content for doc in documents]
        return [list(vec) for vec in self._model.encode(texts)]

    def embed_query(self, text: str) -> List[float]:
        return list(self._model.encode(text))


class HashEmbeddingModel(BaseEmbeddingModel):
    def __init__(self, model_name: str, dimensions: int = 256):
        self.model_name = model_name
        self.dimensions = dimensions

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return _TOKEN_PATTERN.findall(text.lower())

    def _vectorize(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokenize(text):
            slot = hash(token) % self.dimensions
            vector[slot] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        return [self._vectorize(doc.page_content) for doc in documents]

    def embed_query(self, text: str) -> List[float]:
        return self._vectorize(text)


def build_embeddings(model_name: str, cache_dir: Path) -> BaseEmbeddingModel:
    try:
        return SentenceTransformerWrapper(model_name, cache_dir)
    except EmbeddingInitError as exc:
        _LOG.warning("Falling back to hash embeddings: %s", exc)
        return HashEmbeddingModel(model_name)
