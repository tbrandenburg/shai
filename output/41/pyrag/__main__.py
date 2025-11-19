"""CLI entrypoint for pyrag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import typer
except Exception:  # pragma: no cover - Typer optional
    typer = None
else:
    # Temporarily prefer the argparse CLI because newer Typer releases emit
    # incompatible Rich help output inside the constrained uv runtime.
    typer = None

from . import pipeline
from .config import InvalidConfigError, load_config
from .logging import configure_logging


def _execute_with_args(args: Dict[str, Any]) -> int:
    try:
        config = load_config(args)
    except InvalidConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    configure_logging(config.verbose, config.log_file)
    result = pipeline.execute(config)
    print(pipeline.format_answer(result))
    return 0


if typer:
    app = typer.Typer(add_completion=False)

    @app.command()
    def run(
        pdf: Path = typer.Option(Path("tests/fixtures/dummy.pdf"), help="Path to PDF"),
        query: str = typer.Option(..., prompt=True, help="Question to answer"),
        chunk_size: int = typer.Option(750, help="Chunk size"),
        chunk_overlap: int = typer.Option(100, help="Chunk overlap"),
        embedding_model: str = typer.Option(
            "sentence-transformers/all-MiniLM-L6-v2", help="Embedding model"
        ),
        k: int = typer.Option(4, help="Top-K documents"),
        persist_index: bool = typer.Option(
            False,
            "--persist-index",
            "--no-persist-index",
            help="Persist FAISS index",
        ),
        persist_chunks: bool = typer.Option(
            False,
            "--persist-chunks",
            "--no-persist-chunks",
            help="Persist chunk cache",
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            "--no-verbose",
            help="Verbose logging",
        ),
        retriever_backend: str = typer.Option("faiss", help="Retriever backend"),
        llm_backend: str = typer.Option("context-only", help="LLM backend"),
        log_file: Optional[Path] = typer.Option(None, help="Optional log file path"),
    ) -> None:
        args = {
            "pdf_path": pdf,
            "query": query,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "embedding_model": embedding_model,
            "k": k,
            "persist_index": persist_index,
            "persist_chunks": persist_chunks,
            "retriever_backend": retriever_backend,
            "llm_backend": llm_backend,
            "verbose": verbose,
            "log_file": log_file,
        }
        status = _execute_with_args(args)
        raise typer.Exit(code=status)

    def cli() -> None:
        app()
else:

    def cli() -> None:
        parser = argparse.ArgumentParser(description="Offline pyrag pipeline")
        parser.add_argument(
            "--pdf", type=Path, required=False, default=Path("tests/fixtures/dummy.pdf")
        )
        parser.add_argument("--query", required=True)
        parser.add_argument("--chunk-size", type=int, default=750)
        parser.add_argument("--chunk-overlap", type=int, default=100)
        parser.add_argument(
            "--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2"
        )
        parser.add_argument("--k", type=int, default=4)
        parser.add_argument("--persist-index", action="store_true")
        parser.add_argument("--persist-chunks", action="store_true")
        parser.add_argument("--retriever-backend", default="faiss")
        parser.add_argument("--llm-backend", default="context-only")
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--log-file", type=Path)
        namespace = parser.parse_args()
        args = {
            "pdf_path": namespace.pdf,
            "query": namespace.query,
            "chunk_size": namespace.chunk_size,
            "chunk_overlap": namespace.chunk_overlap,
            "embedding_model": namespace.embedding_model,
            "k": namespace.k,
            "persist_index": namespace.persist_index,
            "persist_chunks": namespace.persist_chunks,
            "retriever_backend": namespace.retriever_backend,
            "llm_backend": namespace.llm_backend,
            "verbose": namespace.verbose,
            "log_file": namespace.log_file,
        }
        sys.exit(_execute_with_args(args))


if __name__ == "__main__":
    cli()
