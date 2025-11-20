# Feature 4 – LangChain Design

## 1. Objectives & Guardrails
- Reintroduce every real dependency from the legacy script (DoclingLoader, HybridChunker, MarkdownHeaderTextSplitter, HuggingFaceEmbeddings, Milvus, PromptTemplate, `create_stuff_documents_chain`, `create_retrieval_chain`, HuggingFaceEndpoint) inside the modular `pyrag/` packages without expanding the public configuration surface beyond the nine sanctioned env vars.
- Keep `uv run pyrag` as the only user command. `PipelineSettings` remains the single normalization point and must continue to validate/emit sanitized telemetry.
- Preserve offline determinism for CI by keeping every module protocol-based and providing explicit fallbacks that tests can assert.
- Emit granular RunSummary and logging metadata so later docs/tests can prove the real libraries executed.

## 2. Dependency & Packaging Plan (`pyproject.toml`, `uv.lock`)
1. Add runtime dependencies:
   - `langchain==0.3.x` (core chains + PromptTemplate).
   - `langchain-community` for Milvus vector store utilities.
   - `langchain-milvus` (preferred high-level adapter around pymilvus) or `pymilvus>=2.4` if required by the adapter.
   - `langchain-huggingface` (HuggingFaceEndpoint + embeddings wrappers).
   - `langchain-docling` + `docling==1.x` for loader + HybridChunker integration.
   - `langchain-text-splitters` (MarkdownHeaderTextSplitter) if not bundled.
   - `huggingface-hub` to satisfy HuggingFaceEndpoint transport.
   - `tenacity` (already indirect) reused for retries if not provided by langchain.
2. Keep dev dependencies intact; ensure Ruff/Pytest extras remain available.
3. Regenerate `uv.lock` after editing `pyproject.toml` so Feature 4 build/test artifacts can cite exact versions in `lib_build_log.md`.

## 3. Configuration Surface (`pyrag/config.py`, `.env.example`, `README.md`)
1. `PipelineSettings` remains unchanged externally but must expose derived constants required by the new modules:
   - Add internal-only properties (e.g., `docling_source_url`, `docling_headers`, `docling_export_type`, `prompt_template`, `hf_repo_id`) computed from constants and not read from env.
   - Provide `hf_token` override hook strictly via constructor (tests may pass) without reading env.
2. Extend `snapshot()` to include backend fingerprints (`docling_version`, `hf_model`, `milvus_mode`) populated by the runner for telemetry.
3. `.env.example` and README updates will describe the reinstated dependencies, caches, and nine env knobs without exposing new variables; note that Docling + HuggingFace assets download automatically under `DOC_CACHE_DIR`.

## 4. Module-Level Design

### 4.1 Loader (`pyrag/loader.py`)
- **Imports**: `from langchain_docling import DoclingLoader as LC_DoclingLoader, ExportType`, `from langchain_docling.loaders import LoaderConfig`, `from langchain_docling.pipeline import PipelineConfig`, `from langchain_docling.utils import checksum_file` (or equivalent), `from tenacity import retry, wait_exponential, stop_after_attempt` for retries.
- **Dataclasses**:
  - Keep `DocChunk` but add optional fields `strategy: str` and `docling_meta: dict[str, Any]` to capture loader-level metadata such as `section_path`, `doc_id`, `docling_version`.
- **Initialization**:
  - `DoclingLoader.__init__(self, *, source_url: str | None = None, export_type: ExportType | None = None)` resolves defaults from constants and stores a `cache_path` under `settings.doc_cache_dir / "docling_source.json"` plus a `download_dir` for PDF artifacts.
- **Load Flow**:
  1. `_ensure_payload(settings)` orchestrates download + parse:
     - If `docling_source.json` exists and `settings.validation_enabled` is false or the checksum matches the remote file, reuse cache.
     - Otherwise instantiate `LC_DoclingLoader` with `LoaderConfig(output_format="doc_chunks")` referencing `settings.doc_cache_dir` and call `.load()`; persist the JSON payload for re-runs.
  2. Wrap downloads with tenacity to retry 3 times before raising `LoaderError`.
  3. Convert LangChain `Document` objects into `DocChunk` objects preserving `page`, `section_hierarchy`, `doc_id`, and ordering.
- **Fallback**:
  - If Docling import fails or the network is unreachable, log `status="fallback"`, emit deterministic stub JSON identical to Feature 3 to preserve offline behavior; set `doc_chunk.metadata["strategy"] = "fallback"` so downstream telemetry flags it.
- **Metrics**:
  - Populate `RunSummary.metrics["loader"]` with `doc_count`, `docling_version`, `cache_hit`, `elapsed_ms`, and `strategy` fields.

### 4.2 Chunker (`pyrag/chunker.py`)
- **Structure**:
  - Rename the concrete class to `DoclingHybridChunker` (retain import alias `HybridChunker = DoclingHybridChunker` for backward compatibility).
  - Accept `DoclingLoader` output along with `PipelineSettings` and instantiate the real `docling.chunking.HybridChunker` when `settings.export_type == ExportType.DOC_CHUNKS`.
  - When Markdown fallback is needed, instantiate `MarkdownHeaderTextSplitter` from `langchain_text_splitters` configured with `chunk_size`/`chunk_overlap`.
- **Implementation**:
  1. `_chunk_doc_chunks(documents, settings)` uses Docling chunker to produce structured tokens; convert each `ChunkingResult` into the local `Chunk` dataclass, copying metadata and injecting `"strategy": "doc_chunks"`.
  2. `_chunk_markdown(markdown_docs, settings)` handles fallback using Markdown splits and tags metadata with `"strategy": "markdown"`.
- **Validation**:
  - If neither strategy yields chunks, raise `ChunkerError` describing the source doc and chunk settings.
- **Metrics**:
  - `RunSummary.metrics["chunker"]` stores `chunk_count`, `strategy_counts`, `chunk_size`, `chunk_overlap`.

### 4.3 Embedder (`pyrag/embedder.py`)
- **Renaming**: Introduce `HuggingFaceEmbedder` (exported as `MiniLMEmbedder` for compatibility) implementing `EmbedderProtocol`.
- **Implementation**:
  1. Lazily instantiate `HuggingFaceEmbeddings` from `langchain_huggingface.embeddings` using `model_name="sentence-transformers/all-MiniLM-L6-v2"`, `cache_folder=settings.doc_cache_dir`, `model_kwargs={"device": "cpu"}`.
  2. Provide `_vectorize(payloads, settings)` that calls `embed_documents` / `embed_query` methods. Wrap `huggingface_hub.utils._LoginError` and network timeouts; when they occur, emit deterministic hash fallback identical to existing `_hash_embedding` helper.
  3. Track whether the fallback path executed via `self._using_fallback` for telemetry.
- **Public API**:
  - `embed()` returns `list[Embedding]` with metadata enriched with `model_name`, `strategy` (`"huggingface"` or `"hash"`), and the originating chunk id.
  - `embed_query()` mirrors this for queries.
- **Metrics**:
  - Add `RunSummary.metrics["embedder"] = {"count": len(embeddings), "model": model_name, "strategy": "huggingface"|"hash", "elapsed_ms": ...}`.

### 4.4 Storage (`pyrag/storage.py`)
- **Imports**: `from langchain_milvus import Milvus` (or `from langchain_community.vectorstores import Milvus` depending on version), `from pymilvus import MilvusException`.
- **Dataclasses**:
  - Extend `StorageHandle.metadata` to include `insert_count`, `collection`, `dimension`, `index_type`, `metric_type`, and `mode` (`"lite"` vs `"remote"`).
- **Implementation**:
  1. `MilvusStore.__init__(self, settings: PipelineSettings | None = None)` accepts optional settings so default runner can instantiate with config.
  2. `persist(embeddings, collection)` now:
     - Creates Milvus connection: if `settings.milvus_uri` begins with `file://`, spin up Milvus Lite by pointing LangChain Milvus at the derived path; otherwise forward the URI/credentials.
     - Calls `Milvus.from_documents(documents, embedding=self._dummy_embedding)` or directly uses `.add_texts()` with vectors precomputed from `Embedding` objects.
     - Returns `StorageHandle` with `teardown` closing the Milvus connection or deleting Lite directories via `ExitStack`.
  3. Provide `.query(query_vector, top_k)` by delegating to `self._vectorstore.similarity_search_with_score_by_vector`.
  4. Translate `MilvusException` instances into `StorageError` with actionable messaging (include sanitized URI from `logging.redact_uri`).
- **Metrics**: Add `RunSummary.metrics["storage"]` entries for `collection`, `milvus_uri_redacted`, `insert_count`, `dimension`, `index_type`, `metric_type`, and `status`.

### 4.5 Search (`pyrag/search.py`)
- **Imports**: `from langchain.prompts import PromptTemplate`, `from langchain.chains.combine_documents import create_stuff_documents_chain`, `from langchain.chains import create_retrieval_chain`, `from langchain_huggingface import HuggingFaceEndpoint`, plus `RunnableConfig` if needed for telemetry.
- **LangChain wiring**:
  1. `LangChainSearch.__init__(self, store: StorageProtocol, embedder: EmbedderProtocol, *, prompt_template: str | None = None, llm_repo_id: str = "mistralai/Mistral-7B-Instruct-v0.2")` stores dependencies and builds prompt templates lazily.
  2. `ask()` now obtains a `vectorstore` adapter from `storage_handle` (Milvus store should expose `.as_vectorstore()` or we wrap `Milvus` instance). Build a retriever via `.as_retriever(search_kwargs={"k": settings.top_k})`.
  3. Instantiate `HuggingFaceEndpoint(repo_id=llm_repo_id, max_new_tokens=512, temperature=0.1, timeout=120)` without a token by default. If `settings.hf_token` is provided (only via tests/private config), pass it but never log.
  4. Build `prompt = PromptTemplate(template=DEFAULT_PROMPT_TEMPLATE, input_variables=["context", "question"])`, `stuff_chain = create_stuff_documents_chain(llm, prompt)`, `qa_chain = create_retrieval_chain(retriever, stuff_chain)`.
  5. Execute `response = qa_chain.invoke({"input": settings.query_text})` capturing `response["answer"]` and `response["context"]/"source_documents"` metadata for `RetrievedSource` entries.
- **Fallback summarizer**:
  - Catch `HuggingFaceHubAPIError`, `ValueError`, or HTTP 401. When triggered, log `status="degraded"`, call deterministic summarizer built from the retrieved sources (similar to current `_summarize`) and mark `SearchResult.answer` as `(degraded) ...` while still returning `sources`.
  - If retriever itself fails (Milvus query returns 0), raise `SearchError` with remediation instructions per LR-RETRIEVE.
- **Telemetry**:
  - Add `RunSummary.metrics["search"] = {"retriever": "Milvus", "llm": "HuggingFaceEndpoint", "repo_id": ..., "latency_ms": ..., "fallback": bool}` plus per-source metadata (score, page, section) appended to `SearchResult` for CLI/validation.

### 4.6 Pipeline Runner (`pyrag/pipeline.py`)
- **Dependencies**:
  - Update default instantiations to `DoclingLoader(settings)`? Instead, modify `PipelineRunner.__init__` to accept factories or instantiate lazily inside `run()` so `settings` are available when constructing loader/chunker/embeder/storage/search.
  - Keep DI-friendly signature but set placeholders to `None` and instantiate when `run()` receives settings.
- **Lifecycle**:
  1. On `run()`, always rehydrate owned modules with the current settings (Docling requires cache dir, storage requires URI, search needs prompt). Use `ExitStack` to manage storage teardown and potential Milvus Lite cleanup.
  2. Expand `_capture_stage()` to accept `version_hook` so we can attach backend versions (Docling, LangChain, Milvus) to metrics.
  3. After `RunSummary` creation, include `RunSummary.metrics["settings"] = settings.snapshot()` and stage-level statuses.
- **Validation Hooks**:
  - After search, call `validation.validate(summary)` if `settings.validation_enabled`, else log warning but still record counts for CLI.

### 4.7 CLI & Logging (`pyrag/cli.py`, `pyrag/logging.py`)
- Update CLI help copy to mention Docling + LangChain stack now active.
- `_render_summary()` should display new telemetry fields (Docling strategy, chunker strategy, embedding model, Milvus URI redacted, LLM fallback status). Add a separate table for retrieved sources showing page/section metadata.
- Logging module remains mostly unchanged but should expose `configure_json()` helper or at least ensure extra dicts (including nested metadata) are serializable.

### 4.8 Validation (`pyrag/validation.py`)
- Expand thresholds:
  - Validate that `summary.metrics["loader"]["status"] != "fallback"` unless `settings.validation_enabled` is False.
  - Confirm `len(summary.search_result.sources) >= settings.top_k` when data volume allows.
  - Add check ensuring `summary.metrics["embedder"]["strategy"] == "huggingface"` when HuggingFace service responded; if fallback triggered, validation should fail unless QA explicitly disabled validation via env.
- Return a dict containing previous counts plus `"llm_status"`, `"retrieval_latency_ms"`, etc., for CLI display.

### 4.9 Exceptions & Telemetry (`pyrag/exceptions.py`, `pyrag/logging.py`)
- Keep hierarchy but add specialized errors if needed (e.g., `MilvusConnectionError(StorageError)` with more context). Ensure all new errors inherit from existing classes.
- Provide helper in `logging.py` to log sanitized URIs + fallback statuses.

## 5. Testing & Offline Strategy (`output/42/tests/*.py`)
1. **Unit Tests (`tests/test_modules.py`)**
   - Replace direct `MiniLMEmbedder` hash forcing with fixtures that patch `HuggingFaceEmbeddings` and `HuggingFaceEndpoint` to deterministic stubs while asserting import paths were touched.
   - Add tests verifying `DoclingLoader` writes cache + metadata when actual library is patched to emit controlled docs; include fallback test when `langchain_docling` raises.
   - Ensure `MilvusStore` leverages dependency injection to substitute an in-memory fake so tests run without real Milvus, but still confirm the adapter is invoked (spy on `langchain_milvus.Milvus` constructor when available).
   - Cover search fallback path by forcing `HuggingFaceEndpoint` to raise 401 and asserting `SearchResult.answer` includes `(degraded)` prefix and metrics flag fallback.
2. **Pipeline Tests (`tests/test_pipeline.py`)**
   - Use monkeypatch fixtures to plug fakes for DoclingLoader/Milvus/HuggingFace so the pipeline can execute offline while verifying `PipelineRunner` still logs real class names inside metrics.
   - Add a new test ensuring validation fails when loader fallback occurs while validation is enabled.
3. **CLI Smoke Test**
   - Update CLI test to assert summary table includes the new telemetry rows and that sanitized Milvus URI is shown.

## 6. Documentation & Logs
- `lib_build_log.md`: Document every file touched plus commands for dependency installation (`uv pip install langchain-docling ...`), config migrations, cache directories created during manual verification.
- `lib_docs.md`: Later documentation task will summarize CLI/doc changes; design ensures the necessary telemetry is available (Docling version, Milvus mode, HuggingFace fallback flags).
- `lib_test_results.md`: Future validation agent will log Ruff/Pytest/CLI commands. This design ensures tests have deterministic seams to reference (fakes, toggles, metrics fields).

## 7. Execution Order Recommendation
1. Update dependencies (`pyproject.toml`/`uv.lock`) and regenerate virtual env caches.
2. Implement module upgrades in the order: loader → chunker → embedder → storage → search → pipeline → validation/logging/CLI.
3. Refresh `.env.example` + README once new behavior is in place.
4. Extend unit + integration tests ensuring offline determinism.
5. Run Ruff format/check, pytest, and dual CLI executions; capture evidence in `lib_build_log.md` and `lib_test_results.md`.

This design keeps the scope tightly aligned with `lib_architecture.md` while enumerating the exact file edits, data surfaces, exception handling, and telemetry plumbing needed to ship Feature 4 with confidence.
