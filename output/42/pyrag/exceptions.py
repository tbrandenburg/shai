"""Centralized exception hierarchy for pyrag modules."""

from __future__ import annotations


class PyragError(RuntimeError):
    """Base exception for all pyrag failures."""


class LoaderError(PyragError):
    """Raised when the loader cannot fetch or parse documents."""


class ChunkerError(PyragError):
    """Raised when chunk normalization fails."""


class EmbedderError(PyragError):
    """Raised when embeddings cannot be produced."""


class StorageError(PyragError):
    """Raised for Milvus/Lite persistence issues."""


class SearchError(PyragError):
    """Raised when retrieval/search cannot produce useful answers."""


class ValidationError(PyragError):
    """Raised when validation determines the run summary is invalid."""


__all__ = [
    "PyragError",
    "LoaderError",
    "ChunkerError",
    "EmbedderError",
    "StorageError",
    "SearchError",
    "ValidationError",
]
