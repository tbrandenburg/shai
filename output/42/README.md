# pyrag UV Packaging Prototype

This directory hosts the UV-managed packaging scaffold for the Docling-powered modular RAG CLI. The goal is to make `uv run pyrag` the single deterministic entrypoint while keeping the loader → chunker → embedder → storage → search → validation pipeline modular.

## Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed globally (`pip install uv` or download the standalone binary)
- Milvus Lite requirements are optional because the default storage falls back to an in-memory vector store

## Setup & Usage
1. `uv sync` – create the virtual environment from `pyproject.toml` / `uv.lock`.
2. `uv run pyrag` – execute the orchestration CLI (default settings shown in `.env.example`).
3. Optional overrides can be supplied inline, e.g. `uv run pyrag -- --top-k 10 --metrics-verbose true` to test precedence without editing `.env`.
4. Supporting commands defined under `[tool.uv.scripts]`:
   - `uv run format`
   - `uv run lint`
   - `uv run test`
   - `uv run validate`

## Configuration
Copy `.env.example` to `.env` and adjust only the nine supported keys:

| Variable | Purpose / Range |
| --- | --- |
| `DOC_CACHE_DIR` | Writable folder for Docling cache artifacts (default `.pyrag_cache`). |
| `MILVUS_URI` | Optional external Milvus endpoint; leave blank to auto-provision `file://<DOC_CACHE_DIR>/milvus-lite`. |
| `MILVUS_COLLECTION` | Target collection (1-64 chars, alphanumeric/underscore, default `pyrag_docs`). |
| `TOP_K` | Retrieval depth (default 5, clamped to 1–20). |
| `CHUNK_SIZE` | Chunk size for the hybrid splitter (default 1000, allowed 200–2000). |
| `CHUNK_OVERLAP` | Overlap between chunks (default 200, must be `0 ≤ overlap < chunk_size`). |
| `LOG_LEVEL` | Python logging level (INFO default; accepts DEBUG/INFO/WARNING/ERROR). |
| `VALIDATION_ENABLED` | Boolean toggle for validation (default true). |
| `METRICS_VERBOSE` | Boolean toggle for extra per-stage telemetry (default false). |

## Project Layout
```
pyrag/
  __init__.py           # package export surface
  __main__.py           # python -m pyrag entrypoint
  cli.py                # Typer CLI with env hydration + rich metrics output
  config.py             # PipelineSettings dataclass + env loader with validation
  exceptions.py         # Shared exception hierarchy for uniform error handling
  loader.py             # Docling-aware loader returning DocChunk dataclasses
  chunker.py            # Hybrid chunker producing Chunk instances with metadata
  embedder.py           # MiniLM embedder + deterministic fallback that never needs a token
  storage.py            # MilvusStore abstraction backed by an in-memory vector table
  search.py             # LangChain-style orchestrator emitting SearchResult objects
  pipeline.py           # PipelineRunner wiring modules + telemetry snapshots
  validation.py         # RunSummary validation + aggregate counters
  logging.py            # Structured logging helper
```

Tests live in `tests/test_pipeline.py` and currently act as smoke coverage for the `PipelineRunner`. Expand these tests in later milestones when the Docling + Milvus integrations are fully wired up.

## Feature 2 Highlights
- Modular RAG stack mirrors the design doc: loader → chunker → embedder → storage → search → validation.
- Each module exposes a dataclass/Protocol contract so QA can inject fakes for deterministic tests.
- `sentence-transformers/all-MiniLM-L6-v2` is loaded lazily without requiring a HuggingFace token; offline runs fall back to deterministic hash vectors.
- Milvus storage defaults to an in-memory FLAT index while preserving the lifecycle/teardown contract for future Lite integrations.
- `uv run pyrag` now prints per-stage metrics, a sanitized settings snapshot, and the retrieved answer with supporting sources.
