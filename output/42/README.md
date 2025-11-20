# pyrag UV Packaging Prototype

`pyrag` is a UV-managed packaging scaffold for a Docling + LangChain retrieval pipeline. It keeps `uv run pyrag run` as the single command that hydrates a modular loader → chunker → embedder → storage → retrieval chain backed by DoclingLoader, HybridChunker, MarkdownHeaderTextSplitter, HuggingFaceEmbeddings, Milvus (Lite or remote), and a HuggingFaceEndpoint-powered QA chain.

## Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) installed globally (`pip install uv` or download the standalone binary)
- Internet access the first time Docling and HuggingFace assets are cached (subsequent runs reuse files under `DOC_CACHE_DIR`)
- Optional external Milvus endpoint; the CLI provisions Milvus Lite under `DOC_CACHE_DIR` when `MILVUS_URI` is blank

## Quick Start
1. `uv sync` – create the virtual environment from `pyproject.toml` / `uv.lock`.
2. `uv run pyrag run` – execute the orchestration CLI using `.env` (or the defaults from `.env.example`).
3. Override any of the nine sanctioned settings inline, e.g. `uv run pyrag run --top-k 8 --metrics-verbose true`.
4. Offline or airgapped validation: run `uv run pyrag run --validation-enabled false` to allow the deterministic fallback summarizer when HuggingFaceEndpoint is unreachable.

The CLI automatically loads `.env`, applies Typer option overrides, and prints a telemetry table summarizing Docling strategy, chunk counts, embedding model, Milvus URI/mode, and LLM fallback status. Validation failures (e.g., LLM fallback triggered while `VALIDATION_ENABLED=true`) exit with code 1 so CI can detect regressions.

## Configuration Surface
Copy `.env.example` to `.env` and adjust only the variables below. Each value is validated inside `pyrag/config.py`; invalid inputs fall back to documented defaults with a CLI warning.

| Variable | Purpose / Range |
| --- | --- |
| `DOC_CACHE_DIR` | Writable folder for Docling cache artifacts, downloaded PDFs, and HuggingFace model weights (default `.pyrag_cache`). |
| `MILVUS_URI` | Optional external Milvus endpoint; blank ⇒ `file://<DOC_CACHE_DIR>/milvus-lite` with automatic lifecycle management. |
| `MILVUS_COLLECTION` | Target collection (1-64 chars, alphanumeric/underscore, default `pyrag_docs`). |
| `TOP_K` | Retrieval depth (default 5, clamped within 1–20). |
| `CHUNK_SIZE` | Docling/Markdown chunk size (default 1000, allowed 200–2000). |
| `CHUNK_OVERLAP` | Overlap between chunks (default 200, must satisfy `0 ≤ overlap < chunk_size`). |
| `LOG_LEVEL` | Python logging level (default INFO; accepts DEBUG/INFO/WARNING/ERROR/CRITICAL). |
| `VALIDATION_ENABLED` | Boolean gate for `pyrag.validation.validate` (default true). Disable when HuggingFaceEndpoint is unreachable and the degraded summarizer must be accepted. |
| `METRICS_VERBOSE` | Boolean toggle for additional per-stage telemetry (default false). |

All other knobs—Docling source URL, export type, prompt template, HuggingFaceEndpoint repo ID, Milvus index topology, etc.—are internal constants enforced by `PipelineSettings` for determinism.

## Pipeline Overview
- **Loader (`pyrag/loader.py`)** – wraps `langchain_docling.DoclingLoader`, caches the exported JSON payload, and falls back to deterministic sample data when Docling is unavailable.
- **Chunker (`pyrag/chunker.py`)** – invokes Docling's HybridChunker when export_type is `DOC_CHUNKS`, otherwise reuses Markdown header splits; telemetry records which path ran.
- **Embedder (`pyrag/embedder.py`)** – calls `langchain_huggingface.HuggingFaceEmbeddings` (MiniLM) with fallback hashing when HuggingFace cannot be reached.
- **Storage (`pyrag/storage.py`)** – persists vectors into Milvus (Lite or remote) via `langchain_milvus`, capturing collection details and sanitized URIs.
- **Search (`pyrag/search.py`)** – builds a PromptTemplate, stuff chain, and retrieval chain using HuggingFaceEndpoint; if the endpoint errors, a deterministic summarizer produces a `(degraded)` answer.
- **Pipeline (`pyrag/pipeline.py`)** – wires the modules, tracks RunSummary metrics, and calls `pyrag.validation.validate` before rendering CLI output.

Tests live in `tests/test_modules.py` and `tests/test_pipeline.py`, exercising both real imports (patched) and deterministic fallbacks so CI remains offline-friendly.

## Sample `uv run pyrag run --validation-enabled false`
```
[07:30:29] Starting pyrag pipeline {'doc_cache_dir': '/.../.pyrag_cache', 'milvus_uri': 'file:///.../.pyrag_cache/milvus-lite', 'top_k': 5, ...}
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric            ┃ Value                                                    ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Documents         │ 1                                                        │
│ Chunks            │ 1                                                        │
│ Embeddings        │ 1                                                        │
│ Hits              │ 1                                                        │
│ Docling Strategy  │ docling                                                  │
│ Embedder Model    │ sentence-transformers/all-MiniLM-L6-v2                   │
│ Milvus URI        │ file:///.../.pyrag_cache/milvus-lite                     │
│ Milvus Mode       │ lite                                                     │
│ LLM Fallback      │ yes                                                      │
└───────────────────┴──────────────────────────────────────────────────────────┘
Answer: (degraded) Retrieved 1 chunks for 'Which are the main AI models in Docling?'.
Top sources:
  - (0.22) doc-0:0:0 ... Docling Technical Report placeholder ...
Pipeline completed successfully.
```

Use this sample to cross-check telemetry expectations (`Docling Strategy`, `Milvus Mode`, `LLM Fallback`, etc.) when updating docs or writing tests. When HuggingFaceEndpoint becomes reachable, the `LLM Fallback` row flips to `no` and the answer text comes directly from the hosted model.
