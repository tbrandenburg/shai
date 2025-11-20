# Feature 4 – LangChain Integration Architecture

## 1. Objective & Inputs
- Restore the end-to-end Docling → LangChain RAG stack using the real libraries enumerated in `lib_requirements.md` while keeping the UV pipeline contract described in `rag_architecture.md` and the configuration guardrails from `env_architecture.md`.
- Document how `pyrag/pipeline.py` wires loader, chunker, embedder, storage, and search orchestrators together so downstream design/implementation tasks can reason about dependency boundaries, fallbacks, and telemetry expectations.
- Inputs consulted: `output/42/lib_requirements.md`, `output/42/rag_architecture.md`, `output/42/env_architecture.md`, `output/42/pyrag/pipeline.py`.

## 2. Configuration & Control Flow
1. `uv run pyrag` executes `pyrag.__main__`, which calls `pyrag.cli.main()`.
2. CLI loads `.env` → Typer overrides → internal defaults exactly as defined in `env_architecture.md`, materializing a `PipelineSettings` instance that exposes only the nine public knobs (cache dir, Milvus URI/collection, chunk size/overlap, validation, metrics verbosity, log level, top_k).
3. Settings snapshot is logged (with `MILVUS_URI` redacted) and passed into `PipelineRunner.run(settings)`; no module re-reads environment variables.
4. `PipelineRunner` (see `pyrag/pipeline.py`) instantiates stage objects when callers do not inject fakes, executes stages sequentially, captures per-stage metrics, and emits a `RunSummary` consumed by validation/CLI printing.

## 3. Logical Topology
```
uv run pyrag
  ➜ pyrag.cli.load_settings()  ➜  PipelineRunner(settings)
        │                                 │
        │        ┌────────────────────────────────────────────────────────────┐
        │        │Dependency tree composed inside PipelineRunner.__init__(): │
        │        │  DoclingLoader → HybridChunker → MiniLMEmbedder →          │
        │        │  MilvusStore → LangChainSearch (retriever + LLM chain)     │
        │        └────────────────────────────────────────────────────────────┘
        │                                 │
        └──────────────────────────▶ RunSummary + telemetry + validation
```
Each module retains the protocol-oriented seams established in Feature 2 so pytest can replace heavy dependencies with fakes even though defaults now instantiate the real LangChain stack.

## 4. Component Architecture
### 4.1 Docling Loader (`pyrag/loader.py`)
- Constructs `langchain_docling.DoclingLoader` configured for the Docling Technical Report URL and `ExportType.DOC_CHUNKS` (Markdown optional).
- Downloads/caches artifacts beneath `DOC_CACHE_DIR`, validating checksums and retrying failures with exponential backoff.
- Emits metadata per document (`doc_id`, `page`, hierarchy) that downstream stages require for provenance.
- Exposes methods parameterized only by `PipelineSettings` fields; chunker configuration (chunk size/overlap) remains derived internally so public env vars stay fixed.

### 4.2 Chunking & Splitting (`pyrag/chunker.py`)
- Primary path instantiates `docling.chunking.HybridChunker` using loader outputs and the `CHUNK_SIZE`/`CHUNK_OVERLAP` controls from `PipelineSettings`.
- When Markdown export is requested (internal fallback), uses `langchain_text_splitters.MarkdownHeaderTextSplitter` with equivalent overlap sizing.
- Maintains metadata showing which strategy produced a chunk (e.g., `chunk.metadata["strategy"] ∈ {"doc_chunks","markdown"}`) so QA can verify fallbacks.
- Logs effective size/overlap and chunk counts into `RunSummary.metrics["chunker"]`.

### 4.3 Embeddings (`pyrag/embedder.py`)
- Instantiates `langchain_huggingface.embeddings.HuggingFaceEmbeddings` with `model_name="sentence-transformers/all-MiniLM-L6-v2"`, `cache_folder=DOC_CACHE_DIR`, CPU execution, and no token requirement.
- Provides `embed()` and `embed_query()` so retrieval uses identical vector spaces.
- When HuggingFace download fails or the anonymous endpoint throttles, emits a warning and falls back to a deterministic stub vector while preserving count metrics so the CLI can still run offline; summary marks fallback usage for telemetry consumers.

### 4.4 Storage (`pyrag/storage.py`)
- Wraps `langchain_milvus.Milvus` (or `Milvus.from_documents`) and receives `milvus_uri`/`milvus_collection` from settings.
- Blank URI ⇒ auto-provision Milvus Lite at `<DOC_CACHE_DIR>/milvus-lite/<run-id>`; non-blank URIs validated exactly as described in `env_architecture.md` before connection attempts.
- Persists embeddings, returning a `StorageHandle` that includes the collection name, resolved URI, embedding dimension, insert count, and a teardown callback that closes Lite instances via `ExitStack`.
- Captures index metadata (`metric_type`, `index_type`) plus insert counts in `RunSummary.metrics["storage"]`.

### 4.5 Retrieval & LLM Chains (`pyrag/search.py`)
- Builds a Milvus retriever (`vectorstore.as_retriever(search_kwargs={"k": settings.top_k})`).
- Defines a `PromptTemplate` that mirrors the original script prompts and passes it into `create_stuff_documents_chain` (answer synthesizer) + `create_retrieval_chain` (retriever → LLM pipeline).
- Uses `langchain_huggingface.HuggingFaceEndpoint` with repo id `mistralai/Mistral-7B-Instruct-v0.2`, deliberately omitting a token. Optional token injection remains an internal hook for tests/maintainers.
- If HuggingFaceEndpoint rejects anonymous calls, the chain logs an explicit warning, switches to a deterministic summarizer (e.g., `ContextCompressor + template`), and marks the response as degraded while keeping CLI output structure consistent (question banner, answer, sources table).
- Records retrieval latency, LLM latency, and each source’s metadata (`chunk_id`, `score`, `page`, `section`) in both stdout and `RunSummary.metrics["search"]`.

## 5. Pipeline Runner Responsibilities (`pyrag/pipeline.py`)
- Uses dependency-injection friendly constructor parameters for loader/chunker/embedder/storage/search; tests can pass fakes to avoid real dependency costs.
- Inside `run()`, ensures `settings.ensure_valid()` enforces the nine-var contract, re-instantiates owned dependencies with the resolved settings (e.g., `MilvusStore(settings.milvus_uri)`), and executes each stage under `_capture_stage()` to automatically log elapsed time and counts.
- Maintains `ExitStack` lifecycle management so Milvus teardown always runs, even when downstream stages raise.
- Stores metrics dictionary keyed by stage name for telemetry, ready for Feature 4 validation/doc obligations (e.g., verifying embed count matches chunk count).

## 6. Fallback & Availability Strategies
| Stage | Primary Failure Mode | Fallback / Behavior |
| --- | --- | --- |
| Loader | Network/Retrieval failure | Retry 3x with backoff; if cached file exists, reuse it; otherwise raise `LoaderError` and emit remediation tips while keeping cache directory untouched. |
| Chunker | Doc chunks missing / Markdown export only | Automatically switch to `MarkdownHeaderTextSplitter`; log warning and set `strategy="markdown"` for transparency. |
| Embedder | HF model download blocked | Warn, fall back to deterministic vector hash so CLI/testing remains deterministic; still log failure for QA evidence. |
| Storage | Milvus URI unreachable | If blank → ensure Lite path exists; if remote → surface TLS/auth instructions and abort before ingestion; all failures recorded in metrics with `status="failed"`. |
| Retrieval/LLM | HuggingFaceEndpoint throttles or returns 401 | Log and fall back to deterministic summarizer; CLI exit code remains success only if retrieval succeeded (per `lib_requirements` LR-RETRIEVE). |
| Pipeline Validation | Downstream stages missing outputs | `pyrag.validation.validate` asserts counts/latencies and raises with actionable errors; when `VALIDATION_ENABLED=false`, runner logs WARN banner for auditability. |

## 7. Telemetry & Run Evidence
- `_capture_stage()` already records elapsed milliseconds and item counts; Feature 4 expands the `enrich` payloads per stage to include backend identifiers (Docling version, chunk strategy, HF model id, Milvus index metadata, retrieval latencies) so QA can prove real libraries executed.
- `RunSummary.settings_snapshot` stores the nine env values (sanitized) for correlation with `lib_test_results.md` logs.
- CLI prints a human-friendly summary (question, answer, sources). Structured metrics feed `lib_build_log.md` and `lib_test_results.md` to satisfy traceability.

## 8. Offline & Testing Seams
- Because every module exposes a protocol, pytest fixtures can inject lightweight doubles (e.g., `FakeLoader`, `InMemoryMilvus`). Feature 4 requires that these doubles stay drop-in replacements for the real LangChain classes so CI can operate without Milvus/HF services.
- Tests assert that the default runner instantiates the real classes (by spying on import paths) and that `RunSummary.metrics` captures backend names, preventing regressions that remove Docling/LangChain usage.
- For offline CLI usage, cached Docling PDFs and embedding model artifacts under `DOC_CACHE_DIR` keep repeated runs fast even when disconnected.

## 9. Traceability to Requirements
- LR-ORCH satisfied by PipelineRunner orchestration and RunSummary metrics.
- LR-LOAD/LR-CHUNK fulfilled via DoclingLoader + HybridChunker + Markdown fallback design.
- LR-EMBED ensures HuggingFaceEmbeddings default, CPU execution, metadata capture, and fallback stub.
- LR-STORE implements Milvus (Lite or remote) with lifecycle + metrics.
- LR-RETRIEVE addresses PromptTemplate + LangChain chain wiring + HuggingFaceEndpoint fallback, keeping CLI output shape.
- LR-CONF & LR-VAL tie configuration flow and validation gates directly to `env_architecture.md`.
- LR-TEST acknowledges DI seams/offline doubles enabling Ruff/pytest/CLI automation without extra env knobs.

This architecture now unblocks design and implementation phases by providing a concrete wiring model that honors the UV CLI contract while reinstating every LangChain/Docling dependency the user requested.
