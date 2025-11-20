"""Typer-based CLI for the pyrag pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from pyrag.config import emit_settings_snapshot, load_settings
from pyrag.exceptions import ValidationError
from pyrag.logging import configure
from pyrag.pipeline import PipelineRunner, RunSummary
from pyrag.validation import validate

console = Console()
app = typer.Typer(help="Docling-powered modular RAG pipeline", add_completion=False)


@app.callback()
def _root_callback() -> None:
    """Placeholder group callback to keep the `run` subcommand exposed."""


def _hydrate_environment(env_file: Path | None) -> None:
    """Load environment variables once at startup."""
    if env_file and env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)


def _build_overrides(**kwargs: Any) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if kwargs.get("doc_cache_dir") is not None:
        overrides["DOC_CACHE_DIR"] = str(kwargs["doc_cache_dir"])
    if kwargs.get("milvus_uri") is not None:
        overrides["MILVUS_URI"] = str(kwargs["milvus_uri"])
    if kwargs.get("milvus_collection") is not None:
        overrides["MILVUS_COLLECTION"] = str(kwargs["milvus_collection"])
    if kwargs.get("top_k") is not None:
        overrides["TOP_K"] = str(kwargs["top_k"])
    if kwargs.get("chunk_size") is not None:
        overrides["CHUNK_SIZE"] = str(kwargs["chunk_size"])
    if kwargs.get("chunk_overlap") is not None:
        overrides["CHUNK_OVERLAP"] = str(kwargs["chunk_overlap"])
    if kwargs.get("log_level") is not None:
        overrides["LOG_LEVEL"] = str(kwargs["log_level"])
    if kwargs.get("validation_enabled") is not None:
        overrides["VALIDATION_ENABLED"] = str(kwargs["validation_enabled"])
    if kwargs.get("metrics_verbose") is not None:
        overrides["METRICS_VERBOSE"] = str(kwargs["metrics_verbose"])
    return overrides


def _render_summary(summary: RunSummary, validation_counts: dict[str, int]) -> None:
    loader_meta = summary.metrics.get("loader", {})
    embedder_meta = summary.metrics.get("embedder", {})
    storage_meta = summary.metrics.get("storage", {})
    search_meta = summary.metrics.get("search", {})

    table = Table(title="pyrag pipeline summary", expand=True)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_row("Documents", str(validation_counts["documents"]))
    table.add_row("Chunks", str(validation_counts["chunks"]))
    table.add_row("Embeddings", str(validation_counts["embeddings"]))
    table.add_row("Hits", str(validation_counts["hits"]))
    table.add_row("Docling Strategy", str(loader_meta.get("strategy", "")))
    table.add_row("Embedder Model", str(embedder_meta.get("model", "")))
    table.add_row("Embedder Strategy", str(embedder_meta.get("strategy", "")))
    table.add_row(
        "Collection",
        storage_meta.get("collection", summary.settings_snapshot.get("milvus_collection", "")),
    )
    table.add_row(
        "Milvus URI",
        storage_meta.get("milvus_uri", summary.settings_snapshot.get("milvus_uri", "")),
    )
    table.add_row("Milvus Mode", str(storage_meta.get("mode", "")))
    table.add_row("LLM Fallback", "yes" if search_meta.get("fallback") else "no")
    table.add_row("Question", search_meta.get("question", ""))
    console.print(table)

    console.print("[bold]Answer[/bold]:", summary.search_result.answer)
    console.print("[bold]Top sources:[/bold]")
    for source in summary.search_result.sources:
        snippet = (source.text or "").strip().splitlines()[0][:120]
        page = source.metadata.get("page", "?")
        section = source.metadata.get("section", "?")
        console.print(f"  - ({source.score:.2f}) {source.chunk_id} p{page} {section}: {snippet}")


@app.command("run", help="Execute the modular RAG pipeline end-to-end.")
def run_command(
    env_file: Path | None = typer.Option(  # noqa: B008
        default=None,
        exists=False,
        file_okay=True,
        dir_okay=False,
        help="Optional .env file path to load before running the pipeline (defaults to .env).",
    ),
    doc_cache_dir: Path | None = typer.Option(  # noqa: B008
        default=None,
        help="Override DOC_CACHE_DIR (default: .pyrag_cache).",
        dir_okay=True,
        file_okay=False,
    ),
    milvus_uri: str | None = typer.Option(  # noqa: B008
        default=None,
        help="Override MILVUS_URI (leave blank for auto Milvus Lite).",
    ),
    milvus_collection: str | None = typer.Option(  # noqa: B008
        default=None,
        help="Override MILVUS_COLLECTION (alphanumeric/underscore, max 64 chars).",
    ),
    top_k: int | None = typer.Option(  # noqa: B008
        default=None,
        help="Override TOP_K retrieval depth (1-20).",
    ),
    chunk_size: int | None = typer.Option(  # noqa: B008
        default=None,
        help="Override CHUNK_SIZE (200-2000).",
    ),
    chunk_overlap: int | None = typer.Option(  # noqa: B008
        default=None,
        help="Override CHUNK_OVERLAP (must be < chunk size).",
    ),
    log_level: str | None = typer.Option(  # noqa: B008
        default=None,
        help="Override LOG_LEVEL (DEBUG/INFO/WARNING/ERROR).",
    ),
    validation_enabled: str | None = typer.Option(  # noqa: B008
        default=None,
        help="Explicitly toggle VALIDATION_ENABLED (true/false).",
    ),
    metrics_verbose: str | None = typer.Option(  # noqa: B008
        default=None,
        help="Toggle METRICS_VERBOSE for per-stage telemetry.",
    ),
) -> None:
    _hydrate_environment(env_file)
    overrides = _build_overrides(
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
    settings = load_settings(overrides or None)
    configure(settings.log_level)
    snapshot = emit_settings_snapshot(settings)
    console.log("Starting pyrag pipeline", snapshot)
    runner = PipelineRunner()
    summary = runner.run(settings)

    try:
        counts = validate(summary)
    except ValidationError as exc:  # pragma: no cover - displayed via console
        console.print(f"[bold red]Validation failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    _render_summary(summary, counts)
    console.print("[bold green]Pipeline completed successfully.[/bold green]")


def main() -> None:
    """Entry point used by `python -m pyrag` and `uv run pyrag`."""
    app()
