# Feature 2 – Modular RAG Design

This design document translates the architecture in `rag_architecture.md` into implementable modules, files, dataclasses, and validation hooks so Feature 2 can proceed deterministically. As the data-engineer, the emphasis is on reliable data movement, invariants, and observability that guarantee 99.9% pipeline availability, sub-hour data freshness, zero data loss, and comprehensive governance.

## 1. System Overview & Sequencing

```
uv run pyrag → pyrag.__main__.main() → pyrag.cli.main()
      ↓                 ↓
load_settings() ──▶ PipelineRunner(settings)
      ↓
Loader → Chunker → Embedder → Storage → Search → Validation
```

- **Execution Contract**: `pyrag/cli.py` instantiates `PipelineSettings`, then calls `pyrag/pipeline.py:run(settings)` which wires the remaining modules and assembles a `RunSummary` consumed by `pyrag/validation.py`.
- **Failure policy**: if any stage emits 0 records, throws a typed exception, or violates invariants, the pipeline aborts early with actionable messaging surfaced to the CLI and metrics stream.
- **Observability**: each module logs structured metrics to stdout and attaches them to `RunSummary.metrics` for QA capture in `rag_test_results.md`.

## 2. Shared Dataclasses & Configuration Files

| Artifact | File | Fields & Notes |
| --- | --- | --- |
| `PipelineSettings` | `pyrag/config.py` | `source_url`, `export_type` (`Enum`), `doc_cache_dir`, `chunk_size`, `chunk_overlap`, `headers`, `milvus_uri`, `milvus_collection`, `query_text`, `top_k`, `hf_token`, `log_level`, `validation_enabled`, `metrics_verbose`. Includes `from_env()` factory, `.snapshot()` serializer, and validation ensuring `chunk_size > chunk_overlap ≥ 0` + `top_k ≥ 1`. |
| `DocChunk` | `pyrag/loader.py` | `id`, `text`, `metadata` (pages, section, checksum, source_url), `tokens`. Preserves Docling metadata for provenance. |
| `Chunk` | `pyrag/chunker.py` | `id`, `text`, `metadata` (doc_id, section_path, chunk_mode, token_estimate), `order_index`. |
| `Embedding` | `pyrag/embedder.py` | `id`, `vector` (`list[float]` or `np.ndarray`), `metadata` (chunk_id, order_index). |
| `StorageHandle` | `pyrag/storage.py` | `collection_name`, `dimension`, `milvus_uri`, `teardown: Callable[[], None]`, `metadata` (index_type, insert_count). |
| `SearchResult` | `pyrag/search.py` | `question`, `answer`, `sources: list[RetrievedSource]`, `latency_ms`, `top_k`, `confidence_scores`. `RetrievedSource` captures `chunk_id`, `score`, `text`, `metadata`. |
| `RunSummary` | `pyrag/pipeline.py` | `documents`, `chunks`, `embeddings`, `search_result`, `metrics`, `settings_snapshot`. Each list entry is typed (e.g., `documents: list[DocChunk]`). |
| Exception hierarchy | `pyrag/exceptions.py` (new) | `PyragError` base + `LoaderError`, `ChunkerError`, `EmbedderError`, `StorageError`, `SearchError`, `ValidationError`. Modules raise these for uniform CLI handling. |

### Configuration Surfaces
- `.env.example` enumerates every `PipelineSettings` field with defaults (Docling Technical Report URL, `DOC_CHUNKS`, `chunk_size=1000`, `chunk_overlap=200`, `MILVUS_URI=` blank for Lite, `MILVUS_COLLECTION=docling_demo`, `QUERY_TEXT="Which are the main AI models in Docling?"`, `TOP_K=5`).
- `pyrag/config.py` loads `.env` using `python-dotenv`, merges CLI overrides (placeholder `--config` for future use), and logs sanitized settings via `rich` table.
- Validation ensures directories exist (create `doc_cache_dir`), ensures `MILVUS_URI` is a valid URI or defaults to Lite path, and warns (does not fail) when `hf_token` is absent.

## 3. Module Blueprints

### 3.1 Loader (`pyrag/loader.py`)
- **Classes**: `LoaderProtocol` (`Protocol`), `DoclingLoader` implementing `load(settings) -> list[DocChunk]`.
- **Dependencies**: `docling`, `httpx`/`requests`, `tenacity` for retries, `rich` for progress.
- **Workflow**:
  1. Download Docling Technical Report to `settings.doc_cache_dir` (skip if checksum unchanged).
  2. Use Docling export API with `settings.export_type` to produce structured chunks.
  3. Map Docling outputs to `DocChunk` dataclasses.
- **Metrics**: `doc_count`, `bytes_downloaded`, `elapsed_ms`, `cache_hit` flag.
- **Error Handling**: `LoaderError` with remediation tips (set `SOURCE_URL`, check network, adjust `EXPORT_TYPE`). Retries exponential backoff (max 3) for HTTP errors; fails fast on schema drift.

### 3.2 Chunker (`pyrag/chunker.py`)
- **Classes**: `ChunkerProtocol`, `HybridChunker`.
- **Inputs**: `list[DocChunk]`, `PipelineSettings`.
- **Logic**: Normalizes Docling chunk spans into consistent `Chunk` objects, applying `chunk_size` + `chunk_overlap` when fallback splitting needed. Metadata retains `doc_id`, `section_path`, `chunk_mode`, `token_estimate` (use `tiktoken` or heuristics).
- **Metrics**: `chunk_count`, `median_tokens`, `mode` (`DOC_CHUNKS`/`MARKDOWN`).
- **Errors**: Raises `ChunkerError` when zero chunks produced or if chunk size settings invalid.

### 3.3 Embedder (`pyrag/embedder.py`)
- **Classes**: `EmbedderProtocol`, `MiniLMEmbedder`.
- **Dependencies**: `sentence-transformers`, optional `numpy`.
- **Initialization**: `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu", use_auth_token=None)`; logs when cached weights reused. Optionally surfaces `settings.metrics_verbose` data.
- **Methods**: `embed(chunks: Sequence[Chunk]) -> list[Embedding]`, `embed_query(text: str) -> Embedding`.
- **Metrics**: `embeddings_count`, `latency_per_100`, `cache_status`.
- **Errors**: Wraps download failures with `EmbedderError` suggesting `uv run pyrag --prefetch` (future) and verifying disk space.

### 3.4 Storage (`pyrag/storage.py`)
- **Classes**: `StorageProtocol`, `MilvusStore`, `MilvusSession` context manager.
- **Dependencies**: `pymilvus`, `milvus-lite`.
- **Workflow**:
  1. Resolve `milvus_uri`: use `.env` override or create temporary Lite directory via `tempfile.TemporaryDirectory()` stored on `StorageHandle`.
  2. Initialize collection (dim auto-detected from embedding vector length). Default `index_type="FLAT"`, `metric_type="COSINE"`.
  3. Insert embeddings, flush, optionally load index into memory.
  4. `persist()` returns `StorageHandle` with `teardown` that drops Lite resources when pipeline completes.
  5. `query()` accepts `Embedding` or raw query text (calls embedder) and respects `top_k`.
- **Metrics**: `collection_name`, `inserted_count`, `dim`, `milvus_uri`, `index_type`, `latency_ms`.
- **Errors**: `StorageError` on connection failures, index mismatches, or invalid URIs; includes instructions for setting `MILVUS_URI`.

### 3.5 Search (`pyrag/search.py`)
- **Classes**: `SearchOrchestrator`, `LangChainSearch` implementing `ask(handle, query_text, settings) -> SearchResult`.
- **Dependencies**: `langchain`, `langchain-milvus`, `langchain-huggingface`, `rich` for pretty output.
- **Workflow**:
  1. Use `MilvusStore.query` with query embedding to retrieve docs.
  2. Compose LangChain chain with optional HF generation (only when `hf_token` + `settings.generation_model`). Otherwise, build deterministic textual summary from retrieved contexts.
  3. Return `SearchResult` capturing answer, `sources` list with chunk metadata, and latency.
- **Metrics**: `top_k`, `retrieval_latency`, `confidence_scores`.
- **Errors**: `SearchError` when zero hits; includes remediation suggestions (increase `top_k`, verify loader output).

### 3.6 Validation (`pyrag/validation.py`)
- **Function**: `validate(summary: RunSummary) -> None`.
- **Checks**: `len(summary.documents) ≥ 1`, `len(chunks) ≥ 1`, `len(embeddings) == len(chunks)`, `summary.search_result.top_k ≥ settings.top_k`, `summary.search_result.answer.strip() != ""`.
- **Extras**: Provide `collect_metrics(summary) -> dict` to share aggregated counts with QA; include remediation hints in exception message.

### 3.7 Orchestrator (`pyrag/pipeline.py`)
- **Class**: `PipelineRunner` with `run(settings) -> RunSummary`.
- **Responsibilities**: instantiate modules (dependency injection via optional overrides for testing), manage lifecycle (e.g., call `handle.teardown()`), capture metrics, catch typed exceptions to add context before bubbling to CLI.
- **Logging**: Use `rich.console` to print stage banners and structured metrics tables for each module.

## 4. Error Handling & Governance

- **Exceptions**: central `pyrag/exceptions.py` ensures CLI handles `PyragError` uniformly (log, exit code 1, suggestion). Unexpected exceptions wrapped into `PyragError("Unexpected failure")` with preserved traceback in verbose mode.
- **Retry strategy**: apply tenacity/backoff to loader downloads and embedder model fetches. Storage/query operations rely on Milvus internal retries but add guard rails for timeouts.
- **Data retention**: `doc_cache_dir` keeps source artifacts; `StorageHandle` teardown cleans Milvus Lite directories. Document these behaviors in README + CLI help.
- **Governance**: Settings snapshot stored inside `RunSummary` for audit; future telemetry exporters can publish to OpenTelemetry without altering module APIs.

## 5. Testing & Mocking Strategy

| Test Target | File | Purpose | Notes |
| --- | --- | --- | --- |
| Loader unit tests | `tests/test_loader.py` | Mock Docling client to verify DOC_CHUNKS vs Markdown handling, retry logic, metadata preservation. | Use `responses` or in-memory fixtures; validate checksum skip logic. |
| Chunker unit tests | `tests/test_chunker.py` | Ensure chunk sizing, overlap, metadata propagation, and `chunk_mode` flag. | Provide synthetic `DocChunk` fixtures. |
| Embedder tests | `tests/test_embedder.py` | Inject fake `SentenceTransformer` to avoid downloads; verify CPU fallback and caching messages. | Use monkeypatch to stub `.encode`. |
| Storage tests | `tests/test_storage.py` | Start Milvus Lite in temp dir, validate `StorageHandle` teardown, index params, and query responses using dummy vectors. | Provide fixture to limit resource usage by reducing dim to 3. |
| Search orchestrator tests | `tests/test_search.py` | Mock Milvus retriever + LangChain chain to ensure answer formatting + optional HF token behavior. | Validate zero-hit surfaces `SearchError`. |
| Pipeline integration | `tests/test_pipeline.py` | Use dependency-injected fake loader/storage to simulate deterministic outputs, ensuring `RunSummary` counts align and validation gating works. | Already present stub should be updated to leverage new protocols. |
| CLI smoke test | `tests/test_cli.py` | Run Typer command via `CliRunner` to ensure `.env` loading and exit codes behave. | Mocks network requests to keep offline. |

- **Mocks/Stubs**: Provide `pyrag/testing/fakes.py` with `FakeLoader`, `FakeChunker`, `FakeEmbedder`, `FakeStorage`, `FakeSearch` to support integration tests without heavy dependencies.
- **Test Utilities**: `tests/conftest.py` sets up temporary directories, environment variables, and ensures `PYRAG_TEST_MODE=1` disables actual downloads.
- **CI Hooks**: `uv ruff format`, `uv ruff check`, and `pytest` executed within Feature 2 QA stage. Tests must run in <5 minutes by caching MiniLM weights (CI doc instructs to pre-run `sentence-transformers` download in pipeline cache step).

## 6. Implementation Checklist

1. **Config & Types**: finalize dataclasses + enums (`ExportType`, `ChunkMode`) and exception hierarchy.
2. **Protocols & Modules**: implement each module in the specified file with constructor defaults, instrumentation, and typed interfaces.
3. **Pipeline Runner**: wire module instances, handle dependency injection, and ensure telemetry + validation ordering.
4. **CLI Updates**: confirm Typer command prints metrics, settings snapshot, and validation verdict; add `--verbose` placeholder.
5. **Docs**: update `.env.example`, `README.md` Feature 2 section, and add module summaries to `pyrag/__init__.py` docstring.
6. **Tests**: create module-level tests plus integration/smoke coverage described above; update `tests/test_pipeline.py` scenario to ensure question answer flow remains deterministic.
7. **Validation Flow**: implement `pyrag/validation.py` gating logic and integrate into CLI exit codes; log success/failure to feed QA artifacts.

## 7. Risk Mitigation & Monitoring

- **Model Download Latency**: Provide CLI log step instructing users to run `uv run pyrag --prefetch` (placeholder) or leverage `SENTENCE_TRANSFORMERS_HOME` caching; document in README + tests use mocked embeddings.
- **Milvus Resource Usage**: Track temporary directory paths in `RunSummary.metrics.storage.temp_path`; ensure `teardown()` invoked even on failure via `contextlib.ExitStack` in `PipelineRunner`.
- **Docling Source Drift**: store SHA256 of downloaded PDF; warn when remote checksum differs and suggest overriding `SOURCE_URL`.
- **Token Confusion**: Embedder never inspects `hf_token`; search module logs `"HF token not provided; using local summarizer"` when absent to reduce user ambiguity.
- **Quality Gates**: `validation.validate` ensures data quality invariants; metrics table printed ensures QA sees doc/chunk/embed counts for every run, satisfying governance.

This design now maps architecture requirements to concrete code artifacts, contracts, and tests so the backend implementation phase can focus on execution without further scope ambiguity.
