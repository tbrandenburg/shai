"""Configuration utilities and settings dataclasses for the pyrag pipeline."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import dotenv_values

from pyrag.logging import get_logger, redact_uri

logger = get_logger(__name__)


class ExportType(str, Enum):
    """Supported Docling export surfaces."""

    DOC_CHUNKS = "DOC_CHUNKS"
    MARKDOWN = "MARKDOWN"


CONFIG_KEYS: tuple[str, ...] = (
    "DOC_CACHE_DIR",
    "MILVUS_URI",
    "MILVUS_COLLECTION",
    "TOP_K",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "LOG_LEVEL",
    "VALIDATION_ENABLED",
    "METRICS_VERBOSE",
)

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
COLLECTION_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,64}$")


@dataclass(frozen=True, slots=True)
class ConfigDefaults:
    doc_cache_dir: Path = Path(".pyrag_cache")
    milvus_collection: str = "pyrag_docs"
    top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 200
    log_level: str = "INFO"
    validation_enabled: bool = True
    metrics_verbose: bool = False


CONFIG_DEFAULTS = ConfigDefaults()
DEFAULT_SOURCE_URL = "https://arxiv.org/pdf/2408.09869"
DEFAULT_EXPORT_TYPE = ExportType.DOC_CHUNKS
DEFAULT_HEADERS: dict[str, str] = {}
DEFAULT_QUERY_TEXT = "Which are the main AI models in Docling?"
DEFAULT_HF_TOKEN: str | None = None
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_LLM_REPO_ID = "mistralai/Mistral-7B-Instruct-v0.2"
DEFAULT_PROMPT_TEMPLATE = (
    "You are a Docling specialist. Use the provided context to answer the question.\n"
    "Context:\n{context}\n\nQuestion: {question}\nAnswer:"
)
DOC_SOURCE_FILENAME = "docling_source.json"


@dataclass(slots=True)
class PipelineSettings:
    """Normalized configuration for the Docling-driven RAG pipeline."""

    doc_cache_dir: Path
    milvus_uri: str
    milvus_collection: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    log_level: str
    validation_enabled: bool
    metrics_verbose: bool
    source_url: str = DEFAULT_SOURCE_URL
    export_type: ExportType = DEFAULT_EXPORT_TYPE
    headers: dict[str, str] = field(default_factory=lambda: DEFAULT_HEADERS.copy())
    query_text: str = DEFAULT_QUERY_TEXT
    hf_token: str | None = DEFAULT_HF_TOKEN

    @property
    def docling_source_path(self) -> Path:
        """Cache file path used to persist Docling exports locally."""

        return self.doc_cache_dir / DOC_SOURCE_FILENAME

    @property
    def docling_source_url(self) -> str:
        return self.source_url

    @property
    def docling_headers(self) -> dict[str, str]:
        return dict(self.headers)

    @property
    def docling_export_type(self) -> ExportType:
        return self.export_type

    @property
    def hf_repo_id(self) -> str:
        return DEFAULT_LLM_REPO_ID

    @property
    def hf_embedding_model(self) -> str:
        return DEFAULT_EMBEDDING_MODEL

    @property
    def prompt_template(self) -> str:
        return DEFAULT_PROMPT_TEMPLATE

    @property
    def milvus_mode(self) -> str:
        return "lite" if self.milvus_uri.startswith("file://") else "remote"

    def snapshot(self) -> dict[str, str]:
        """Return a sanitized dict representation for logging/telemetry."""

        snapshot = asdict(self)
        snapshot["doc_cache_dir"] = str(self.doc_cache_dir)
        snapshot["export_type"] = self.export_type.value
        snapshot["milvus_uri"] = redact_uri(self.milvus_uri)
        snapshot["hf_token"] = "***" if self.hf_token else ""
        snapshot.setdefault("docling_version", "")
        snapshot["hf_model"] = self.hf_embedding_model
        snapshot["hf_repo_id"] = self.hf_repo_id
        snapshot["milvus_mode"] = self.milvus_mode
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
        env_values, ignored = _collect_env(overrides)
        if ignored:
            logger.debug("Ignoring unsupported env vars: %s", ", ".join(sorted(ignored)))
        doc_cache_dir = _resolve_doc_cache_dir(env_values.get("DOC_CACHE_DIR"))
        milvus_uri = _resolve_milvus_uri(env_values.get("MILVUS_URI"), doc_cache_dir)
        milvus_collection = _normalize_collection(env_values.get("MILVUS_COLLECTION"))
        top_k = _parse_int(
            "TOP_K", env_values.get("TOP_K"), minimum=1, maximum=20, default=CONFIG_DEFAULTS.top_k
        )
        chunk_size = _parse_int(
            "CHUNK_SIZE",
            env_values.get("CHUNK_SIZE"),
            minimum=200,
            maximum=2000,
            default=CONFIG_DEFAULTS.chunk_size,
        )
        chunk_overlap = _parse_chunk_overlap(env_values.get("CHUNK_OVERLAP"), chunk_size)
        log_level = _coerce_log_level(env_values.get("LOG_LEVEL"))
        validation_enabled = _parse_bool(
            "VALIDATION_ENABLED",
            env_values.get("VALIDATION_ENABLED"),
            CONFIG_DEFAULTS.validation_enabled,
        )
        metrics_verbose = _parse_bool(
            "METRICS_VERBOSE", env_values.get("METRICS_VERBOSE"), CONFIG_DEFAULTS.metrics_verbose
        )
        settings = cls(
            doc_cache_dir=doc_cache_dir,
            milvus_uri=milvus_uri,
            milvus_collection=milvus_collection,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            log_level=log_level,
            validation_enabled=validation_enabled,
            metrics_verbose=metrics_verbose,
        )
        settings.ensure_valid()
        return settings


def load_settings(overrides: Mapping[str, str] | None = None) -> PipelineSettings:
    """Public helper wired into the CLI."""

    return PipelineSettings.from_env(overrides)


def emit_settings_snapshot(settings: PipelineSettings) -> dict[str, str]:
    """Emit and return a sanitized snapshot for downstream consumers."""

    snapshot = settings.snapshot()
    logger.info("Configuration snapshot", extra={"settings": snapshot})
    return snapshot


def _collect_env(overrides: Mapping[str, str] | None) -> tuple[dict[str, str], set[str]]:
    filtered: dict[str, str] = {}
    ignored: set[str] = set()

    file_values = dotenv_values()
    _merge_into(filtered, file_values, ignored, record_unknown=True)
    _merge_into(filtered, os.environ, ignored, record_unknown=False)
    if overrides:
        _merge_into(filtered, overrides, ignored, record_unknown=True)
    return filtered, ignored


def _merge_into(
    target: dict[str, str],
    source: Mapping[str, str | os.PathLike[str] | None],
    ignored: set[str],
    *,
    record_unknown: bool,
) -> None:
    for key, value in source.items():
        if value is None:
            continue
        str_value = str(value)
        if key in CONFIG_KEYS:
            target[key] = str_value
        elif record_unknown and str_value != "":
            ignored.add(key)


def _resolve_doc_cache_dir(raw: str | None) -> Path:
    path = Path(raw or CONFIG_DEFAULTS.doc_cache_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    if not os.access(path, os.W_OK):
        raise ValueError(f"DOC_CACHE_DIR '{path}' is not writable")
    return path.resolve()


def _resolve_milvus_uri(raw: str | None, cache_dir: Path) -> str:
    if raw and raw.strip():
        return raw.strip()
    derived = cache_dir / "milvus-lite"
    derived.mkdir(parents=True, exist_ok=True)
    return f"file://{derived.resolve()}"


def _normalize_collection(raw: str | None) -> str:
    if not raw:
        return CONFIG_DEFAULTS.milvus_collection
    candidate = raw.strip()
    if COLLECTION_PATTERN.fullmatch(candidate):
        return candidate
    logger.warning(
        "MILVUS_COLLECTION '%s' is invalid; using default '%s'",
        raw,
        CONFIG_DEFAULTS.milvus_collection,
    )
    return CONFIG_DEFAULTS.milvus_collection


def _parse_int(
    name: str,
    raw: str | None,
    *,
    minimum: int,
    maximum: int,
    default: int,
) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s='%s' is not an integer; using default %s", name, raw, default)
        return default
    if value < minimum:
        logger.warning("%s=%s below minimum %s; clamping", name, value, minimum)
        return minimum
    if value > maximum:
        logger.warning("%s=%s above maximum %s; clamping", name, value, maximum)
        return maximum
    return value


def _parse_chunk_overlap(raw: str | None, chunk_size: int) -> int:
    default = CONFIG_DEFAULTS.chunk_overlap
    if raw is None or raw == "":
        return default if default < chunk_size else chunk_size - 1
    try:
        overlap = int(raw)
    except ValueError:
        logger.warning("CHUNK_OVERLAP='%s' is not an integer; using default %s", raw, default)
        return default if default < chunk_size else chunk_size - 1
    if overlap < 0:
        logger.warning("CHUNK_OVERLAP=%s cannot be negative; using default %s", overlap, default)
        return default if default < chunk_size else chunk_size - 1
    if overlap >= chunk_size:
        logger.warning(
            "CHUNK_OVERLAP=%s must be less than CHUNK_SIZE=%s; using default %s",
            overlap,
            chunk_size,
            default,
        )
        return default if default < chunk_size else chunk_size - 1
    return overlap


def _coerce_log_level(raw: str | None) -> str:
    if raw is None or raw == "":
        return CONFIG_DEFAULTS.log_level
    level = raw.strip().upper()
    if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return level
    logger.warning("LOG_LEVEL '%s' is invalid; falling back to %s", raw, CONFIG_DEFAULTS.log_level)
    return CONFIG_DEFAULTS.log_level


def _parse_bool(name: str, raw: str | None, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(
        f"{name} must be one of {sorted(TRUE_VALUES | FALSE_VALUES)}; received '{raw}'"
    )
