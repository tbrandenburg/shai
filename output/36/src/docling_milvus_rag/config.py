"""Configuration loading utilities for the Docling → Milvus RAG pipeline."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_FILE = PROJECT_ROOT / "config" / "defaults.toml"
ENV_PREFIX = "DOCMILVUS_"
VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
ENV_ALIASES: dict[str, str] = {
    "PDFS": "pdf_paths",
    "PDF_PATHS": "pdf_paths",
    "QUESTION": "question",
    "EXPORT_TYPE": "export_type",
    "TOP_K": "retrieval.top_k",
    "CHUNK_SIZE": "chunk.size",
    "CHUNK_OVERLAP": "chunk.overlap",
    "MILVUS_URI": "milvus.uri",
    "COLLECTION": "milvus.collection_name",
    "MILVUS_COLLECTION": "milvus.collection_name",
    "EMBEDDING_MODEL": "embeddings.model_name",
    "LOG_LEVEL": "runtime.log_level",
    "JSON_LOGS": "runtime.json_logs",
    "VERBOSE": "runtime.verbose",
    "CACHE_DIR": "runtime.cache_dir",
}
ENV_LIST_KEYS = {"PDFS", "PDF_PATHS"}


class MilvusConfig(BaseModel):
    """Milvus (Lite) connection settings."""

    model_config = ConfigDict(extra="ignore")

    uri: str = "file:./.milvus/docling.db?mode=memory&cache=shared"
    collection_name: str = "docling_chunks"
    dim: int = 384
    drop_existing: bool = False
    consistency_level: str = "Bounded"


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model_config = ConfigDict(extra="ignore")

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True
    cache_dir: Path | None = None


class ChunkConfig(BaseModel):
    """Document chunking behavior."""

    model_config = ConfigDict(extra="ignore")

    size: int = 800
    overlap: int = 80


class RetrievalConfig(BaseModel):
    """Retrieval tuning parameters."""

    model_config = ConfigDict(extra="ignore")

    top_k: int = 4
    score_threshold: float | None = None

    @field_validator("top_k")
    @classmethod
    def _ensure_top_k(cls, value: int) -> int:
        if value < 1:
            raise ValueError("retrieval.top_k must be >= 1")
        return value


class LLMConfig(BaseModel):
    """Local LLM generation parameters."""

    model_config = ConfigDict(extra="ignore")

    model_path: Path | None = None
    temperature: float = 0.1
    max_tokens: int = 512
    context_window: int = 2048


class RuntimeConfig(BaseModel):
    """Operational toggles for the pipeline."""

    model_config = ConfigDict(extra="ignore")

    json_logs: bool = False
    cache_dir: Path = Path(".cache/docling_milvus_rag")
    wipe_store: bool = False
    persist_store: bool = True
    log_level: str = "INFO"
    verbose: bool = False
    llm_backend: str = "local-llama"

    @field_validator("cache_dir", mode="before")
    @classmethod
    def _coerce_cache_dir(cls, value: Any) -> Path:
        if value is None:
            return Path(".cache/docling_milvus_rag")
        return Path(value)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> str:
        level = str(value).upper()
        if level not in VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level: {value}")
        return level

    @field_validator("llm_backend")
    @classmethod
    def _validate_llm_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local-llama", "stub"}:
            raise ValueError("llm_backend must be either 'local-llama' or 'stub'")
        return normalized


class AppConfig(BaseModel):
    """Aggregate configuration consumed by the pipeline."""

    model_config = ConfigDict(extra="ignore")

    pdf_paths: list[Path] = Field(
        default_factory=lambda: [PROJECT_ROOT / "fixtures" / "dummy.pdf"],
        description="Local PDF paths processed by Docling.",
    )
    question: str = "Summarize the supplied PDF contents."
    export_type: str = "chunks"
    chunk: ChunkConfig = Field(default_factory=ChunkConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    embeddings: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @field_validator("export_type")
    @classmethod
    def _validate_export_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"chunks", "markdown"}:
            raise ValueError("export_type must be either 'chunks' or 'markdown'")
        return normalized

    @field_validator("pdf_paths", mode="before")
    @classmethod
    def _coerce_pdf_paths(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, (str, Path)):
            return [value]
        return list(value)

    @field_validator("pdf_paths")
    @classmethod
    def _resolve_pdf_paths(cls, values: list[Any]) -> list[Path]:
        resolved: list[Path] = []
        for raw in values:
            path = Path(raw)
            if not path.is_absolute():
                path = (PROJECT_ROOT / path).resolve()
            if not path.suffix.lower() == ".pdf":
                raise ValueError(f"{path} is not a PDF file")
            if not path.exists():
                raise ValueError(f"Missing PDF file: {path}")
            resolved.append(path)
        if not resolved:
            raise ValueError("At least one PDF path is required")
        return resolved

    @model_validator(mode="after")
    def _ensure_cache_dir(self) -> "AppConfig":
        cache_dir = (PROJECT_ROOT / self.runtime.cache_dir).resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self.runtime, "cache_dir", cache_dir)
        return self


def load_config(
    cli_args: dict[str, Any] | None = None,
    defaults_path: Path | str | None = None,
) -> AppConfig:
    """Load configuration from defaults, environment variables, and CLI overrides."""

    merged: dict[str, Any] = {}
    defaults_file = _resolve_defaults_path(defaults_path)
    if defaults_file is not None:
        _deep_update(merged, _load_defaults(defaults_file))
    _deep_update(merged, _load_env())
    if cli_args:
        _deep_update(merged, _normalize_cli_args(cli_args))
    return AppConfig.model_validate(merged)


def _load_defaults(defaults_file: Path | None = None) -> dict[str, Any]:
    path = defaults_file or DEFAULTS_FILE
    if path is None or not path.exists():
        return {}
    with path.open("rb") as fp:
        return tomllib.load(fp)


def _resolve_defaults_path(candidate: Path | str | None) -> Path | None:
    env_override = os.environ.get(f"{ENV_PREFIX}CONFIG")
    selected = candidate or env_override
    if selected is None:
        return DEFAULTS_FILE if DEFAULTS_FILE.exists() else None
    path = Path(selected)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _load_env() -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        raw_key = key.removeprefix(ENV_PREFIX)
        normalized_key = raw_key.upper()
        target_path = ENV_ALIASES.get(normalized_key, normalized_key)
        keys = _split_key(target_path)
        parsed_value = _parse_env_value(normalized_key, value)
        _assign(overrides, keys, parsed_value)
    return overrides


def _parse_env_value(raw_key: str, value: str) -> Any:
    if raw_key in ENV_LIST_KEYS:
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _normalize_cli_args(cli_args: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in cli_args.items():
        if value is None:
            continue
        keys = _split_key(key)
        _assign(normalized, keys, value)
    return normalized


def _split_key(key: str) -> list[str]:
    clean = key.strip().lower().replace("__", ".").replace("-", "_")
    parts = [part for part in clean.split(".") if part]
    if not parts:
        raise ValueError(f"Invalid configuration key: {key}")
    return parts


def _assign(target: dict[str, Any], keys: list[str], value: Any) -> None:
    cursor = target
    for key in keys[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[keys[-1]] = value


def _deep_update(target: dict[str, Any], new_values: dict[str, Any]) -> None:
    for key, value in new_values.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(value, dict)
        ):
            _deep_update(target[key], value)
        else:
            target[key] = value
