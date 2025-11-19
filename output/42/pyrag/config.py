"""Configuration utilities and settings dataclasses for the pyrag pipeline."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, MutableMapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class ExportType(str, Enum):
    """Supported Docling export surfaces."""

    DOC_CHUNKS = "DOC_CHUNKS"
    MARKDOWN = "MARKDOWN"


@dataclass(slots=True)
class PipelineSettings:
    """Normalized configuration for the Docling-driven RAG pipeline."""

    source_url: str
    export_type: ExportType
    doc_cache_dir: Path
    chunk_size: int = 1000
    chunk_overlap: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    milvus_uri: str | None = None
    milvus_collection: str = "pyrag_docs"
    query_text: str = "Which are the main AI models in Docling?"
    top_k: int = 5
    hf_token: str | None = None
    log_level: str = "INFO"
    validation_enabled: bool = True
    metrics_verbose: bool = False

    def snapshot(self) -> dict[str, str]:
        """Return a sanitized dict representation for logging/telemetry."""

        snapshot = asdict(self)
        snapshot["doc_cache_dir"] = str(self.doc_cache_dir)
        snapshot["export_type"] = self.export_type.value
        snapshot["hf_token"] = "***" if self.hf_token else ""
        return snapshot

    def ensure_valid(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if self.chunk_size <= self.chunk_overlap:
            raise ValueError("chunk_size must be greater than chunk_overlap")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")

    @classmethod
    def from_env(cls, overrides: Mapping[str, str] | None = None) -> PipelineSettings:
        env = _merge_env(overrides)
        cache_dir = Path(env.get("DOC_CACHE_DIR", ".pyrag_cache")).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        settings = cls(
            source_url=env.get("SOURCE_URL", DEFAULT_SETTINGS.source_url),
            export_type=_coerce_export_type(env.get("EXPORT_TYPE")),
            doc_cache_dir=cache_dir,
            chunk_size=int(env.get("CHUNK_SIZE", DEFAULT_SETTINGS.chunk_size)),
            chunk_overlap=int(env.get("CHUNK_OVERLAP", DEFAULT_SETTINGS.chunk_overlap)),
            headers=_parse_headers(env.get("SOURCE_HEADERS")),
            milvus_uri=env.get("MILVUS_URI") or None,
            milvus_collection=env.get("MILVUS_COLLECTION", DEFAULT_SETTINGS.milvus_collection),
            query_text=env.get("QUERY_TEXT", DEFAULT_SETTINGS.query_text),
            top_k=int(env.get("TOP_K", DEFAULT_SETTINGS.top_k)),
            hf_token=env.get("HF_TOKEN") or None,
            log_level=env.get("LOG_LEVEL", DEFAULT_SETTINGS.log_level),
            validation_enabled=_parse_bool(
                env.get("VALIDATION_ENABLED"), DEFAULT_SETTINGS.validation_enabled
            ),
            metrics_verbose=_parse_bool(
                env.get("METRICS_VERBOSE"), DEFAULT_SETTINGS.metrics_verbose
            ),
        )
        settings.ensure_valid()
        return settings


def _merge_env(overrides: Mapping[str, str] | None) -> MutableMapping[str, str]:
    merged: MutableMapping[str, str] = dict(os.environ)
    if overrides:
        merged.update(overrides)
    return merged


def _coerce_export_type(value: str | None) -> ExportType:
    if value is None:
        return DEFAULT_SETTINGS.export_type
    try:
        return ExportType(value)
    except ValueError as exc:  # pragma: no cover - invalid user value
        raise ValueError(
            f"Unsupported EXPORT_TYPE '{value}'. Expected one of {[e.value for e in ExportType]}."
        ) from exc


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_headers(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        pass
    headers: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers


def load_settings(overrides: Mapping[str, str] | None = None) -> PipelineSettings:
    """Public helper wired into the CLI."""

    return PipelineSettings.from_env(overrides)


DEFAULT_SETTINGS = PipelineSettings(
    source_url="https://arxiv.org/pdf/2408.09869",
    export_type=ExportType.DOC_CHUNKS,
    doc_cache_dir=Path(".pyrag_cache"),
)
