"""Typer-powered CLI for the Docling → Milvus RAG pipeline."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable, NoReturn, Tuple

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .chunker import ChunkBuilder
from .config import AppConfig, PROJECT_ROOT, load_config
from .docling_loader import DoclingIngestor
from .milvus_store import MilvusStore
from .pipeline import Pipeline, PipelineResult

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=False, help="Offline Docling → Milvus runner.")
store_app = typer.Typer(add_completion=False, help="Vector store maintenance commands.")
app.add_typer(store_app, name="store")
DEFAULT_COMMANDS = {"run", "preflight", "store"}


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _version_callback(value: bool) -> None:
    if not value:
        return
    try:
        current = metadata.version("docling-milvus-rag")
    except metadata.PackageNotFoundError:
        current = "0.0.0"
    console.print(f"docling-milvus-rag {current}")
    raise typer.Exit()


@app.command("run")
def run_command(
    pdf: Tuple[Path, ...] = typer.Option(
        (),
        "--pdf",
        help="One or more PDF files to ingest.",
        show_default=False,
        multiple=True,
    ),
    export_type: str | None = typer.Option(
        None,
        "--export-type",
        case_sensitive=False,
        help="Docling export flavor (chunks|markdown).",
    ),
    question: str | None = typer.Option(
        None,
        "--question",
        help="Question forwarded to the answer generator.",
    ),
    top_k: int = typer.Option(4, "--top-k", min=1, max=50, help="Number of chunks retrieved."),
    chunk_size: int | None = typer.Option(
        None,
        "--chunk-size",
        min=128,
        max=5000,
        help="Chunk size fed into the text splitter.",
    ),
    chunk_overlap: int | None = typer.Option(
        None,
        "--chunk-overlap",
        min=0,
        max=2000,
        help="Chunk overlap applied by the splitter.",
    ),
    milvus_uri: str | None = typer.Option(None, "--milvus-uri", help="Milvus Lite URI or path."),
    collection: str | None = typer.Option(None, "--collection", help="Milvus collection name."),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="SentenceTransformer model identifier.",
    ),
    llm_backend: str = typer.Option(
        "local-llama",
        "--llm-backend",
        case_sensitive=False,
        help="Select offline LLM backend (local-llama|stub).",
    ),
    output: Path | None = typer.Option(None, "--output", help="Optional JSON report destination."),
    force: bool = typer.Option(False, "--force", help="Overwrite artifacts and stores when set."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate config without executing the pipeline."),
    config: Path | None = typer.Option(None, "--config", help="Override defaults TOML file."),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        case_sensitive=False,
        help="Logging verbosity (critical|error|warning|info|debug).",
    ),
    json_logs: bool = typer.Option(False, "--json-logs/--no-json-logs", help="Emit JSON logs."),
    verbose: bool = typer.Option(False, "--verbose", help="Echo resolved configuration and progress."),
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
) -> None:
    overrides = _build_run_overrides(
        pdf_paths=list(pdf),
        export_type=export_type,
        question=question,
        top_k=top_k,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        milvus_uri=milvus_uri,
        collection=collection,
        embedding_model=embedding_model,
        llm_backend=llm_backend,
        json_logs=json_logs,
        log_level=log_level,
        verbose=verbose,
    )
    try:
        config_obj = load_config(overrides, defaults_path=config)
    except Exception as exc:  # noqa: BLE001 - emit user-facing error
        _fail(str(exc), code=2)
    if verbose:
        _render_config_summary(config_obj)
    if dry_run:
        console.print("[green]Dry run complete — no pipeline execution performed.")
        raise typer.Exit()
    try:
        result = Pipeline(config_obj).run()
    except Exception as exc:  # noqa: BLE001 - surface clean error
        _fail(f"Pipeline execution failed: {exc}", code=3)
    _render_run_summary(result, config_obj)
    if output is not None:
        _write_output_artifact(output, result, config_obj, force)


@app.command("preflight")
def preflight_command(
    full: bool = typer.Option(False, "--full", help="Also exercise Docling ingestion and chunking."),
    checks: Tuple[str, ...] = typer.Option(
        ("all",),
        "--checks",
        help="Subset of checks to run (env,models,milvus,files,all).",
        multiple=True,
    ),
    config: Path | None = typer.Option(None, "--config", help="Override defaults TOML file."),
    log_level: str = typer.Option("info", "--log-level", case_sensitive=False),
    json_logs: bool = typer.Option(False, "--json-logs/--no-json-logs"),
    verbose: bool = typer.Option(False, "--verbose"),
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
) -> None:
    overrides = _build_runtime_overrides(json_logs, log_level, verbose, llm_backend="stub")
    try:
        config_obj = load_config(overrides, defaults_path=config)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), code=2)
    requested = _normalize_checks(checks)
    results = _perform_preflight_checks(config_obj, requested, full)
    _render_preflight_table(results)
    if not all(result.ok for result in results):
        raise typer.Exit(code=2)


@store_app.command("wipe")
def store_wipe_command(
    collection: str | None = typer.Option(None, "--collection", help="Target collection name."),
    wipe_all: bool = typer.Option(False, "--all", help="Remove the entire Milvus directory."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    config: Path | None = typer.Option(None, "--config", help="Override defaults TOML file."),
    log_level: str = typer.Option("info", "--log-level", case_sensitive=False),
    json_logs: bool = typer.Option(False, "--json-logs/--no-json-logs"),
    verbose: bool = typer.Option(False, "--verbose"),
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
) -> None:
    overrides = _build_runtime_overrides(json_logs, log_level, verbose, llm_backend="stub")
    if collection:
        overrides.setdefault("milvus", {})["collection_name"] = collection
    try:
        config_obj = load_config(overrides, defaults_path=config)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), code=4)
    if not force:
        confirmed = typer.confirm("This will delete vector store artifacts. Continue?", default=False)
        if not confirmed:
            raise typer.Exit()
    if wipe_all:
        target = _resolve_milvus_path(config_obj.milvus.uri)
        if target is None:
            _fail("Cannot derive filesystem path from the provided Milvus URI.", code=4)
        assert target is not None
        _remove_path(target)
        console.print(f"[green]Removed Milvus artifacts at {target}")
        return
    drop_cfg = config_obj.milvus.model_copy(update={"drop_existing": True})
    MilvusStore(cfg=drop_cfg, dim=drop_cfg.dim)
    console.print(
        f"[green]Collection '{drop_cfg.collection_name}' dropped for URI {drop_cfg.uri} (if present)."
    )


@store_app.command("inspect")
def store_inspect_command(
    config: Path | None = typer.Option(None, "--config", help="Override defaults TOML file."),
    log_level: str = typer.Option("info", "--log-level", case_sensitive=False),
    json_logs: bool = typer.Option(False, "--json-logs/--no-json-logs"),
    verbose: bool = typer.Option(False, "--verbose"),
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
) -> None:
    overrides = _build_runtime_overrides(json_logs, log_level, verbose, llm_backend="stub")
    try:
        config_obj = load_config(overrides, defaults_path=config)
    except Exception as exc:  # noqa: BLE001
        _fail(str(exc), code=4)
    table = Table(title="Milvus Store Overview", box=box.SIMPLE_HEAVY)
    table.add_column("Collection", style="bold")
    table.add_column("URI")
    table.add_column("Path Exists")
    table.add_column("Size (bytes)")
    target = _resolve_milvus_path(config_obj.milvus.uri)
    if target and target.exists():
        size = target.stat().st_size
        table.add_row(config_obj.milvus.collection_name, config_obj.milvus.uri, "yes", str(size))
    else:
        table.add_row(config_obj.milvus.collection_name, config_obj.milvus.uri, "no", "0")
    console.print(table)


def _build_run_overrides(
    pdf_paths: list[Path],
    export_type: str | None,
    question: str | None,
    top_k: int,
    chunk_size: int | None,
    chunk_overlap: int | None,
    milvus_uri: str | None,
    collection: str | None,
    embedding_model: str | None,
    llm_backend: str,
    json_logs: bool,
    log_level: str,
    verbose: bool,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if pdf_paths:
        overrides["pdf_paths"] = [str(path) for path in pdf_paths]
    if export_type:
        overrides["export_type"] = export_type
    if question:
        overrides["question"] = question
    overrides.setdefault("retrieval", {})["top_k"] = top_k
    chunk_cfg = overrides.setdefault("chunk", {})
    if chunk_size is not None:
        chunk_cfg["size"] = chunk_size
    if chunk_overlap is not None:
        chunk_cfg["overlap"] = chunk_overlap
    milvus_cfg = overrides.setdefault("milvus", {})
    if milvus_uri:
        milvus_cfg["uri"] = milvus_uri
    if collection:
        milvus_cfg["collection_name"] = collection
    if embedding_model:
        overrides.setdefault("embeddings", {})["model_name"] = embedding_model
    runtime_cfg = overrides.setdefault("runtime", {})
    runtime_cfg["json_logs"] = json_logs
    runtime_cfg["log_level"] = log_level.upper()
    runtime_cfg["verbose"] = verbose
    runtime_cfg["llm_backend"] = llm_backend.lower()
    return overrides


def _build_runtime_overrides(
    json_logs: bool,
    log_level: str,
    verbose: bool,
    llm_backend: str,
) -> dict[str, Any]:
    return {
        "runtime": {
            "json_logs": json_logs,
            "log_level": log_level.upper(),
            "verbose": verbose,
            "llm_backend": llm_backend.lower(),
        }
    }


def _normalize_checks(checks: Iterable[str]) -> list[str]:
    normalized = [check.strip().lower() for check in checks if check.strip()]
    default = ["env", "files", "models", "milvus"]
    if not normalized or "all" in normalized:
        return default
    return [check for check in normalized if check in {"env", "files", "models", "milvus"}]


def _perform_preflight_checks(config: AppConfig, checks: list[str], full: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    if "env" in checks:
        ok = sys.version_info >= (3, 11)
        detail = f"Python {'.'.join(map(str, sys.version_info[:3]))}"
        results.append(CheckResult("Environment", ok, detail))
    if "files" in checks:
        missing = [str(path) for path in config.pdf_paths if not Path(path).exists()]
        ok = not missing
        detail = "All documents present" if ok else f"Missing: {', '.join(missing)}"
        results.append(CheckResult("Documents", ok, detail))
    if "models" in checks:
        ok, detail = _check_models(config)
        results.append(CheckResult("Models", ok, detail))
    if "milvus" in checks:
        ok, detail = _check_milvus(config.milvus.uri)
        results.append(CheckResult("Milvus", ok, detail))
    if full:
        ok, detail = _run_full_ingest(config)
        results.append(CheckResult("Docling ingest", ok, detail))
    return results


def _check_models(config: AppConfig) -> tuple[bool, str]:
    embed_ready = _module_available("sentence_transformers")
    llm_ready = True
    detail_parts = []
    detail_parts.append("sentence-transformers ready" if embed_ready else "sentence-transformers missing")
    if config.llm.model_path:
        llm_path = Path(config.llm.model_path)
        llm_ready = llm_path.exists()
        detail_parts.append("LLM weights present" if llm_ready else f"Missing LLM weights at {llm_path}")
    else:
        detail_parts.append("LLM fallback enabled")
    return embed_ready and llm_ready, "; ".join(detail_parts)


def _check_milvus(uri: str) -> tuple[bool, str]:
    target = _resolve_milvus_path(uri)
    if target is None:
        return True, "Using in-memory Milvus URI"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        detail = f"Filesystem path available at {target}"
        return True, detail
    except PermissionError as exc:
        return False, f"Cannot create Milvus directory: {exc}"


def _run_full_ingest(config: AppConfig) -> tuple[bool, str]:
    try:
        ingestor = DoclingIngestor()
        docs = ingestor.ingest(config.pdf_paths)
        chunks = ChunkBuilder(config.chunk.size, config.chunk.overlap).build(docs)
        return True, f"Ingested {len(config.pdf_paths)} docs → {len(chunks)} chunks"
    except Exception as exc:  # noqa: BLE001
        return False, f"Docling ingestion failed: {exc}"


def _render_config_summary(config: AppConfig) -> None:
    table = Table(title="Resolved Configuration", box=box.SIMPLE_HEAVY)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    table.add_row("PDFs", "\n".join(str(path) for path in config.pdf_paths))
    table.add_row("Question", config.question)
    table.add_row("Chunks", f"size={config.chunk.size}, overlap={config.chunk.overlap}")
    table.add_row("Retrieval", f"top_k={config.retrieval.top_k}")
    table.add_row("Milvus", f"{config.milvus.uri} ({config.milvus.collection_name})")
    table.add_row("Logging", f"level={config.runtime.log_level}, json={config.runtime.json_logs}")
    console.print(table)


def _render_run_summary(result: PipelineResult, config: AppConfig) -> None:
    panel = Panel(
        Text(result.answer.strip() or "No answer generated.", style="cyan"),
        title="Answer",
        expand=False,
    )
    stats = Table(title="Execution Summary", box=box.SIMPLE)
    stats.add_column("Metric", style="bold")
    stats.add_column("Value")
    stats.add_row("Question", config.question)
    stats.add_row("Documents", "\n".join(str(path) for path in config.pdf_paths))
    stats.add_row("Chunks Indexed", str(result.chunks_indexed))
    duration = f"{result.metrics.get('duration_sec', 0):.2f}s"
    stats.add_row("Duration", duration)
    console.print(panel)
    console.print(stats)


def _render_preflight_table(results: list[CheckResult]) -> None:
    table = Table(title="Preflight Summary", box=box.SIMPLE_HEAVY)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail")
    for item in results:
        status = "[green]PASS" if item.ok else "[red]FAIL"
        table.add_row(item.name, status, item.detail)
    console.print(table)


def _write_output_artifact(path: Path, result: PipelineResult, config: AppConfig, force: bool) -> None:
    destination = path if path.is_absolute() else (PROJECT_ROOT / path)
    destination = destination.resolve()
    if destination.exists() and not force:
        _fail(f"Output file {destination} already exists. Use --force to overwrite.", code=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "question": config.question,
        "documents": [str(p) for p in config.pdf_paths],
        "answer": result.answer,
        "chunks_indexed": result.chunks_indexed,
        "metrics": result.metrics,
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"[green]Wrote CLI report to {destination}")


def _module_available(name: str) -> bool:
    from importlib.util import find_spec

    return find_spec(name) is not None


def _resolve_milvus_path(uri: str) -> Path | None:
    if uri.startswith("file:"):
        raw_path = uri.removeprefix("file:").split("?")[0]
    elif "://" in uri:
        return None
    else:
        raw_path = uri
    path = Path(raw_path)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _remove_path(target: Path) -> None:
    if target.is_file():
        target.unlink()
        return
    shutil.rmtree(target, ignore_errors=False)


def _fail(message: str, code: int) -> NoReturn:
    console.print(f"[bold red]Error:[/] {message}")
    raise typer.Exit(code=code)


def _ensure_default_command() -> None:
    if len(sys.argv) <= 1:
        sys.argv.insert(1, "run")
        return
    first = sys.argv[1]
    if first in DEFAULT_COMMANDS or first in {"-h", "--help"}:
        return
    if first.startswith("-") or first not in DEFAULT_COMMANDS:
        sys.argv.insert(1, "run")


def entrypoint() -> None:
    _ensure_default_command()
    app()


if __name__ == "__main__":
    entrypoint()
