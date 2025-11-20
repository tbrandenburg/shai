# Feature 2 – Modular RAG Architecture

## 1. Architectural Intent
- Preserve the Docling → LangChain RAG experience inside the UV-managed `pyrag` package while enforcing loader/chunker/embedder/storage/search separations defined in `rag_requirements.md`.
- Guarantee a deterministic `uv run pyrag` entrypoint that routes through `pyrag.cli` → `pyrag.pipeline.run(settings)` and never requires manual HuggingFace authentication for embeddings.
- Provide a blueprint that downstream design, implementation, and QA phases can trace directly to FR-* requirements, including validation evidence and observability hooks.

## 2. Guiding Principles
1. **Single Orchestrator**: `PipelineRunner` in `pyrag/pipeline.py` owns dependency wiring, lifecycle, and telemetry; modules remain stateless where possible.
2. **Explicit Contracts**: Each stage exposes a protocol-oriented interface with typed dataclasses shared via `pyrag/config.py` and `pyrag/types.py` (or inline definitions).*  A module can be swapped without touching siblings as long as contracts remain satisfied.
3. **Token-Free Embeddings**: `MiniLMEmbedder` always calls `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", use_auth_token=None)`; CLI merely warns when `HF_TOKEN` is absent for optional LLM calls.
4. **Milvus Lite First**: Default storage path uses Milvus Lite with temporary file-backed URI; `.env` overrides gracefully promote to remote Milvus without code changes.
5. **Validation-as-Gate**: The run fails fast if any stage outputs zero results or invariants in `pyrag/validation.py` fail, keeping `uv run pyrag` honest.

_*If a standalone `types.py` does not exist yet, these dataclasses live alongside their owning modules and are imported centrally by `pyrag.pipeline`._

## 3. Component Topology
```
uv run pyrag  →  pyrag.__main__.main()
        ↓              ↓
     pyrag.cli  ──▶ load_settings()
        ↓              ↓
  PipelineRunner(settings)
        ↓
┌──────────────┬──────────┬─────────────┬─────────────┬──────────────┐
│ DoclingLoader│ HybridChunker │ MiniLMEmbedder │ MilvusStore │ LangChainSearch │
└──────────────┴──────────┴─────────────┴─────────────┴──────────────┘
        ↓              ↓                ↓                ↓
   documents      normalized chunks   embeddings     retriever+LLM
        ↓                                                      ↓
                      Validation.validate(run_summary)
```

| Module | File | Key Interfaces | Responsibilities |
| --- | --- | --- | --- |
| CLI & Config | `pyrag/cli.py`, `pyrag/config.py` | `load_settings() -> PipelineSettings` | Bootstraps Typer CLI, loads `.env`, injects defaults, prints run metadata. |
| Loader | `pyrag/loader.py` | `LoaderProtocol.load(settings) -> list[DocChunk]` | Download Docling Technical Report (default), retry network fetches, emit metrics (doc count, size). |
| Chunker | `pyrag/chunker.py` | `ChunkerProtocol.chunk(documents) -> list[Chunk]` | Normalize Docling chunks, apply chunk size/overlap, annotate metadata for provenance. |
| Embedder | `pyrag/embedder.py` | `EmbedderProtocol.embed(chunks) -> list[Embedding]`, `EmbedderProtocol.embed_query(text) -> Embedding` | Host MiniLM model without tokens, compute CPU-friendly embeddings, log cache hits. |
| Storage | `pyrag/storage.py` | `StorageProtocol.persist(embeddings, settings) -> StorageHandle`, `StorageProtocol.query(handle, embedding, top_k)` | Manage Milvus Lite lifecycle, configure index, expose teardown hooks. |
| Search | `pyrag/search.py` | `SearchOrchestrator.ask(handle, query_text, settings) -> SearchResult` | Build LangChain retriever chain, format answer + sources, respect `settings.top_k`. |
| Validation | `pyrag/validation.py` | `validate(run_summary) -> None` | Assert non-empty outputs, equality counts, non-empty answer, raise actionable errors.

## 4. Data & Control Flow
1. **Bootstrap**: `uv run pyrag` executes `[tool.uv.scripts].pyrag`. `pyrag.__main__` calls `pyrag.cli.main()`.
2. **Configuration**: CLI loads `.env` via `python-dotenv`, instantiates `PipelineSettings`, logs the snapshot (excluding secrets), and resolves `SOURCE_URL`, `EXPORT_TYPE`, `MILVUS_URI`, etc.
3. **Loading**: `DoclingLoader.load(settings)` pulls the PDF (default `SOURCE_URL`), emitting `DocChunk` objects containing page spans, section headers, checksum metadata, and caching them under `settings.doc_cache_dir`.
4. **Chunking**: `HybridChunker.chunk(doc_chunks, settings)` flattens Docling chunk metadata into simplified `Chunk` dataclasses (id, text, metadata, order_index, token_estimate). It tracks chunking mode (DOC_CHUNKS vs Markdown fallback) inside metadata for observability.
5. **Embedding**:
   - `MiniLMEmbedder` initializes once per run, calling `SentenceTransformer(... use_auth_token=None)`.
   - If `HF_TOKEN` exists and an alternate model is requested, the embedder logs a warning but still defaults to MiniLM.
   - `embed(chunks)` returns `[Embedding(id, vector, metadata)]` while `embed_query(query_text)` powers retrieval.
6. **Storage**: `MilvusStore.persist(embeddings, settings)` spins up Milvus Lite (file path resolved via `settings.milvus_uri or tempfile.TemporaryDirectory()`), creates/updates collection `settings.milvus_collection`, stores embeddings, and records index parameters. Returns `StorageHandle(collection_name, uri, dim, teardown_callable)`.
7. **Search**: `LangChainSearch.ask(handle, query_text, settings)` uses LangChain Milvus retriever + `create_stuff_documents_chain`. It composes the query embedding via `MiniLMEmbedder`, retrieves top-k docs, and optionally routes final answer generation through `langchain-huggingface` if `HF_TOKEN` and `settings.generation_model` are provided (graceful degrade otherwise).
8. **Validation & Summary**: `PipelineRunner` aggregates `RunSummary(documents, chunks, embeddings, results, metrics, settings_snapshot)`. `validation.validate(summary)` enforces FR-V* constraints before CLI prints the answer + provenance.
9. **Teardown**: Pipeline executes `handle.teardown()` when Milvus Lite uses temp storage; CLI ensures exit code reflects validation success.

## 5. Configuration Surfaces
- `PipelineSettings` (defined in `pyrag/config.py`):
  - Required defaults: `source_url`, `export_type`, `doc_cache_dir`, `chunk_size`, `chunk_overlap`, `milvus_uri`, `milvus_collection`, `query_text`, `top_k`, `hf_token`, `log_level`.
  - Derived knobs: `validation.enabled`, `metrics.verbose` placeholders for future telemetry.
- `.env.example` enumerates each field with descriptions; CLI logs warnings if `.env` missing but continues.
- HuggingFace handling:
  - `hf_token` optional; embedder never requires it.
  - Search module only attempts HF-powered generation when token present; else it prints retrieved contexts and a fallback summary assembled locally.

## 6. Telemetry & Metrics Plan
| Stage | Metrics | Destination |
| --- | --- | --- |
| Loader | doc_count, bytes_downloaded, elapsed_ms, cache_hit | stdout + `RunSummary.metrics.loader` |
| Chunker | chunk_count, avg_tokens, mode | stdout + summary |
| Embedder | embeddings_count, latency_per_100, cache_status | stdout + summary |
| Storage | collection_name, dim, milvus_uri, index_type | stdout |
| Search | top_k, latency_ms, confidence per hit | stdout + structured `SearchResult` |
| Validation | success flag, failing assertion message | stdout + CLI exit code |

Metrics surface via `rich` or logging module so QA can scrape them into `rag_test_results.md`.

## 7. Error Handling & Safety
- **Loader**: retries on HTTP failures; raises `LoaderError` with remediation tips ("Set SOURCE_URL", "Check network").
- **Chunker**: raises `ChunkerError` when zero chunks produced; instructs users to inspect export type.
- **Embedder**: catches model download failures, retries, and provides offline instructions; falls back to CPU automatically.
- **Storage**: wraps Milvus initialization inside context manager, ensuring file handles close even when validation fails.
- **Search**: if retriever returns zero hits, pipeline raises `SearchError` before LLM invocation, causing validation failure with actionable text.
- **Validation**: halts pipeline with aggregated issues (e.g., mismatch counts) so testers immediately see root cause.

## 8. Extensibility Hooks
- Additional retrievers (hybrid BM25) can attach behind `SearchOrchestrator` without disrupting CLI because dependencies are injected via `PipelineSettings`-derived factories.
- Alternate storage backends may implement `StorageProtocol` and register themselves in `settings.storage_backend = "milvus" | "chromadb"` once `rag_design.md` expands scope.
- Observability exporters (OpenTelemetry) can subscribe to pipeline events via a simple pub/sub bus inside `pyrag.logging` if future phases demand it.

## 9. Compliance with Requirements Traceability
| Requirement | Architectural Coverage |
| --- | --- |
| FR-O1/O2/O3/O4 | CLI + pipeline wiring ensures Typer command, `.env` loading, and fast failure semantics. |
| FR-L1–L4 | DoclingLoader contract, metadata preservation, retry guidance handled within loader. |
| FR-C1–C4 | HybridChunker output schema and metrics integrated. |
| FR-E1–E5 | MiniLMEmbedder configuration, CPU fallback, caching metrics. |
| FR-S1–S5 | Milvus Lite default, storage handle, index metadata, teardown. |
| FR-R1–R4 | LangChain search chain design, CLI printing obligations. |
| FR-V1–V3 | Validation gating + messaging strategy. |
| FR-G1–G4 | PipelineSettings definition and `.env.example` coverage. |
| FR-T1–T3 | Pipeline contracts expose seams for mocks, metrics logged for QA artifacts. |

## 10. Deliverables & Next Steps
1. **Design phase** (`rag_design.md`) will map these modules to concrete file/class blueprints, enumerating dataclasses and error types exactly as referenced here.
2. **Implementation phase** will code the modules with instrumentation, ensuring HuggingFace-free embeddings and Milvus Lite bootstrapping match this architecture.
3. **QA phase** will use the metrics and validation hooks described here to prove parity with the legacy Docling script and log evidence in `rag_test_results.md`.
