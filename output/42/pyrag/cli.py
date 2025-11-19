"""Typer-based CLI for the pyrag pipeline."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from pyrag.config import load_settings
from pyrag.exceptions import ValidationError
from pyrag.pipeline import PipelineRunner, RunSummary
from pyrag.validation import validate

console = Console()
app = typer.Typer(help="Docling-powered modular RAG pipeline", add_completion=False)
ENV_FILE_OPTION = typer.Option(
    default=None,
    exists=False,
    file_okay=True,
    dir_okay=False,
    help="Optional .env file path to load before running the pipeline (defaults to .env).",
)


def _hydrate_environment(env_file: Path | None) -> None:
    """Load environment variables once at startup."""
    if env_file and env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)
    else:
        load_dotenv(override=False)


def _render_summary(summary: RunSummary, validation_counts: dict[str, int]) -> None:
    table = Table(title="pyrag pipeline summary", expand=True)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_row("Documents", str(validation_counts["documents"]))
    table.add_row("Chunks", str(validation_counts["chunks"]))
    table.add_row("Embeddings", str(validation_counts["embeddings"]))
    table.add_row("Hits", str(validation_counts["hits"]))
    table.add_row(
        "Collection",
        summary.metrics.get("storage", {}).get(
            "collection", summary.settings_snapshot.get("milvus_collection", "")
        ),
    )
    table.add_row(
        "Milvus URI",
        summary.metrics.get("storage", {}).get(
            "milvus_uri", summary.settings_snapshot.get("milvus_uri", "milvus-lite://memory")
        ),
    )
    table.add_row("Question", summary.metrics.get("search", {}).get("question", ""))
    console.print(table)

    console.print("[bold]Answer[/bold]:", summary.search_result.answer)
    console.print("[bold]Top sources:[/bold]")
    for source in summary.search_result.sources:
        snippet = (source.text or "").strip().splitlines()[0][:120]
        console.print(f"  - ({source.score:.2f}) {source.chunk_id}: {snippet}")


@app.command("run", help="Execute the modular RAG pipeline end-to-end.")
def run_command(
    env_file: Path | None = ENV_FILE_OPTION,
) -> None:
    _hydrate_environment(env_file)
    settings = load_settings()
    console.log("Starting pyrag pipeline", settings.snapshot())
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
