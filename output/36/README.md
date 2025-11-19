# Docling → Milvus RAG (UV Edition)

This directory contains the UV-managed Python project that turns the Docling Colab sample into a reproducible offline pipeline. The code ingests local PDFs, chunks/embeds them, stores embeddings in Milvus Lite, and produces answers via an offline-friendly LLM fallback.

## Quickstart

```bash
uv run docling-milvus-rag --pdf fixtures/dummy.pdf
```

The command above resolves configuration from `config/defaults.toml`, validates that `fixtures/dummy.pdf` exists, runs Docling ingestion → Milvus indexing → answer generation, and prints a Rich-formatted summary. Omitting `--pdf` automatically falls back to the bundled dummy PDF.

## CLI Usage

- `uv run docling-milvus-rag run --help` – View all pipeline options (document paths, retrieval knobs, logging toggles, JSON report output).
- `uv run docling-milvus-rag preflight --checks env --checks models` – Execute readiness checks without touching Milvus or ingesting PDFs.
- `uv run docling-milvus-rag store wipe --force` – Drop the configured Milvus collection (or pass `--all` to delete the entire Lite directory).
- Use `--config <file>` to point at an alternate defaults TOML, `DOCMILVUS_*` environment variables for automation, and `--verbose` to echo the resolved configuration prior to execution.

The CLI is exposed through `[project.scripts]` so the same commands work once the package is installed (e.g., `docling-milvus-rag --pdf ...`).
