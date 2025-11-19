"""Configuration helpers for the pyrag pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


class InvalidConfigError(ValueError):
    """Raised when required settings are missing or inconsistent."""


@dataclass
class PipelineConfig:
    pdf_path: Path
    query: str
    chunk_size: int = 750
    chunk_overlap: int = 100
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    k: int = 4
    persist_index: bool = False
    persist_chunks: bool = False
    retriever_backend: str = "faiss"
    llm_backend: str = "context-only"
    verbose: bool = False
    log_file: Optional[Path] = None
    cache_dir: Path = field(default_factory=lambda: Path(".uv-cache") / "pyrag")
    vectorstore_path: Optional[Path] = None
    chunk_cache_path: Optional[Path] = None
    timeout_seconds: Optional[int] = None
    dry_run: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "pdf_path": str(self.pdf_path),
            "query": self.query,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "k": self.k,
            "persist_index": self.persist_index,
            "persist_chunks": self.persist_chunks,
            "retriever_backend": self.retriever_backend,
            "llm_backend": self.llm_backend,
            "verbose": self.verbose,
            "log_file": str(self.log_file) if self.log_file else None,
            "cache_dir": str(self.cache_dir),
            "vectorstore_path": str(self.vectorstore_path)
            if self.vectorstore_path
            else None,
            "chunk_cache_path": str(self.chunk_cache_path)
            if self.chunk_cache_path
            else None,
            "timeout_seconds": self.timeout_seconds,
            "dry_run": self.dry_run,
        }


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def load_config(cli_args: Optional[Dict[str, Any]] = None) -> PipelineConfig:
    """Create ``PipelineConfig`` from CLI args + env vars."""

    data: Dict[str, Any] = {
        "pdf_path": Path("tests/fixtures/dummy.pdf"),
        "chunk_size": 750,
        "chunk_overlap": 100,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "k": 4,
        "persist_index": False,
        "persist_chunks": False,
        "retriever_backend": "faiss",
        "llm_backend": "context-only",
        "verbose": False,
        "cache_dir": Path(".uv-cache") / "pyrag",
        "dry_run": False,
    }

    if cli_args:
        data.update({k: v for k, v in cli_args.items() if v is not None})

    env_map = {
        "pdf_path": "PYRAG_PDF_PATH",
        "embedding_model": "PYRAG_EMBED_MODEL",
        "retriever_backend": "PYRAG_RETRIEVER",
        "llm_backend": "PYRAG_LLM_BACKEND",
        "cache_dir": "PYRAG_CACHE_DIR",
        "chunk_size": "PYRAG_CHUNK_SIZE",
        "chunk_overlap": "PYRAG_CHUNK_OVERLAP",
        "k": "PYRAG_TOP_K",
        "persist_index": "PYRAG_PERSIST_INDEX",
        "persist_chunks": "PYRAG_PERSIST_CHUNKS",
    }

    for field_name, env_key in env_map.items():
        env_value = os.environ.get(env_key)
        if env_value is None:
            continue
        if field_name in {"chunk_size", "chunk_overlap", "k"}:
            data[field_name] = int(env_value)
        elif field_name in {"persist_index", "persist_chunks"}:
            data[field_name] = _coerce_bool(env_value)
        elif field_name == "cache_dir":
            data[field_name] = Path(env_value)
        else:
            data[field_name] = env_value

    pdf_value = data.get("pdf") or data.get("pdf_path")
    if not pdf_value:
        raise InvalidConfigError("A PDF path is required (use --pdf).")
    pdf_path = Path(str(pdf_value))
    query = data.get("query")
    if not query:
        raise InvalidConfigError("A query is required (pass --query).")
    if not pdf_path.is_file():
        raise InvalidConfigError(f"PDF not found: {pdf_path}")

    cache_dir = Path(data.get("cache_dir") or Path(".uv-cache") / "pyrag")
    cache_dir.mkdir(parents=True, exist_ok=True)

    chunk_cache_raw = data.get("chunk_cache_path")
    chunk_cache_path = (
        Path(str(chunk_cache_raw)) if chunk_cache_raw else cache_dir / "chunks.json"
    )
    vectorstore_raw = data.get("vectorstore_path")
    vectorstore_path = (
        Path(str(vectorstore_raw))
        if vectorstore_raw
        else cache_dir / "vectorstore.json"
    )
    log_file_raw = data.get("log_file")
    log_file = Path(str(log_file_raw)) if log_file_raw else None

    config = PipelineConfig(
        pdf_path=pdf_path,
        query=query,
        chunk_size=int(data.get("chunk_size", 750)),
        chunk_overlap=int(data.get("chunk_overlap", 100)),
        embedding_model=str(data.get("embedding_model")),
        k=int(data.get("k", 4)),
        persist_index=_coerce_bool(data.get("persist_index", False)),
        persist_chunks=_coerce_bool(data.get("persist_chunks", False)),
        retriever_backend=str(data.get("retriever_backend", "faiss")),
        llm_backend=str(data.get("llm_backend", "context-only")),
        verbose=_coerce_bool(data.get("verbose", False)),
        log_file=log_file,
        cache_dir=cache_dir,
        vectorstore_path=vectorstore_path,
        chunk_cache_path=chunk_cache_path,
        timeout_seconds=int(data["timeout_seconds"])
        if data.get("timeout_seconds")
        else None,
        dry_run=_coerce_bool(data.get("dry_run", False)),
    )

    resolve_cache_paths(config)
    return config


def resolve_cache_paths(config: PipelineConfig) -> PipelineConfig:
    """Ensure cache-related directories exist and return the config for chaining."""

    config.cache_dir.mkdir(parents=True, exist_ok=True)
    if config.persist_chunks and config.chunk_cache_path:
        config.chunk_cache_path.parent.mkdir(parents=True, exist_ok=True)
    if config.persist_index and config.vectorstore_path:
        config.vectorstore_path.parent.mkdir(parents=True, exist_ok=True)
    return config
