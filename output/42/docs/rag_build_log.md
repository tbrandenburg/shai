# Feature 2 – Modular RAG Build Log

## 2025-11-19
- Replaced the temporary scaffolding with the planned module structure (loader, chunker, embedder, storage, search, validation, pipeline) so `uv run pyrag` exercises the full Docling→MiniLM→Milvus flow end to end.
- Implemented `PipelineSettings` + `ExportType` with `.from_env()` validation, sanitized snapshots, and new configuration toggles for headers, validation, and verbose metrics. Updated `.env.example` accordingly.
- Added the shared `pyrag.exceptions` hierarchy and threaded typed errors through every module to keep CLI behavior predictable.
- Implemented Docling loader stub that caches JSON payloads, hybrid chunker with overlap controls, MiniLM embedder with hash fallback, Milvus-style storage, and LangChain-like search summaries with provenance-rich `SearchResult` objects.
- Rewrote `PipelineRunner` to capture per-stage telemetry + lifecycle teardown, refreshed the Typer CLI to print structured summaries, and tightened validation to report metric counts.
- Updated smoke tests to consume the new API, refreshed the README with Feature 2 guidance, and documented the implementation details + settings changes here for downstream QA.
