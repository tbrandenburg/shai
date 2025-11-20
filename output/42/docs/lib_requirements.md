# Feature 4 – LangChain Reintegration Requirements

## Objective
- Restore the full LangChain/Docling RAG pipeline that previously lived in the single-file script (see `issue_conversation.md`) so that `uv run pyrag` exercises DoclingLoader → HybridChunker/MarkdownHeaderTextSplitter → HuggingFaceEmbeddings → Milvus vector storage → LangChain retrieval/LLM chains → HuggingFaceEndpoint without shortcuts or mocks.
- Keep the UV-managed packaging guarantees from Features 1–3: the CLI entrypoint stays `uv run pyrag`, only the nine sanctioned environment variables are public, `PipelineSettings` remains the single configuration surface, and Ruff/pytest/CLI validation stay green.
- Provide a contract that downstream architecture/design/implementation/testing phases can trace to when wiring the real libraries into the existing modular files under `output/42/pyrag/` and `output/42/tests/`.

## Inputs & Traceability
- Issue #42 original script and Feature 3 comments calling out the missing imports (`PromptTemplate`, `DoclingLoader`, `HybridChunker`, `MarkdownHeaderTextSplitter`, `HuggingFaceEmbeddings`, `Milvus`, `create_retrieval_chain`, `create_stuff_documents_chain`, `HuggingFaceEndpoint`).
- Existing scope/docs: `rag_requirements.md`, `rag_architecture.md`, `rag_design.md`, `env_requirements.md`, `env_architecture.md`, `README.md`, and the current code in `pyrag/*.py` plus tests in `tests/*.py`.
- Feature 4 artifacts expected downstream: `lib_architecture.md`, `lib_design.md`, `lib_build_log.md`, `lib_docs.md`, `lib_test_results.md`, `lib_defects.md`.

## Stakeholders & Success Metrics
- **Primary user**: Operators who rely on `uv run pyrag` to execute the real Docling → LangChain stack with no manual configuration.
- **Engineering**: Backend devs integrating LangChain libraries, QA verifying regressions, project leadership demanding parity with the reference script.
- **KPIs**: (1) Pipeline runs end-to-end with real dependencies and prints the same style of question/answer/source output as the reference script; (2) tests and Ruff checks remain deterministic; (3) configuration stays limited to the nine env vars; (4) telemetry proves each real library initialized successfully; (5) failure modes surface actionable remediation.

## Scope
- **In**: Replacing placeholder logic inside `loader.py`, `chunker.py`, `embedder.py`, `storage.py`, `search.py`, and `pipeline.py` with the real Docling/LangChain/HuggingFace/Milvus integrations; updating config/logging/validation/tests/docs as required; instrumenting build/test logs.
- **Out**: Adding new env vars or CLI commands, changing Feature 3’s validated defaults, or introducing unrelated RAG features beyond the missing libraries.

## Constraints & Assumptions
- Python 3.11 UV project; only `uv run pyrag` should be required for normal execution.
- Only the nine env vars documented in `env_requirements.md` may be publicly exposed. Everything else (SOURCE_URL, prompt templates, HF tokens, Milvus index params, etc.) must remain internal constants or derived settings.
- HuggingFace embeddings must never require a token; HuggingFaceEndpoint usage must obey the “no token required” promise by default (e.g., rely on open endpoints) and degrade gracefully when optional tokens are absent.
- Pipeline must continue to operate offline once models/cache assets are downloaded; automated tests must be able to inject fakes/mocks so CI does not require Milvus or network access.
- Build/test documentation discipline from earlier features persists: every command needs to be logged in the eventual `lib_build_log.md`/`lib_test_results.md`.

## Functional Requirements
### LR-ORCH (Pipeline Orchestration)
1. `pyrag.pipeline.PipelineRunner` must instantiate the real module classes by default and confirm via logs/metrics that each library initialized (Docling loader, Docling HybridChunker, HuggingFace embeddings, Milvus vector store, LangChain retrieval + HuggingFaceEndpoint answer chain).
2. Dependency injection seams used by tests (`PipelineRunner(loader=..., ...)`) must remain so QA can substitute fakes without hitting the heavy dependencies.
3. `RunSummary` needs to capture library/version metadata per stage so downstream docs/tests can prove LangChain components actually executed.

### LR-LOAD (Docling Loader)
1. `pyrag.loader.DoclingLoader` must import and construct `langchain_docling.DoclingLoader` with `ExportType` support and the Docling Technical Report default URL, caching downloaded artifacts under `DOC_CACHE_DIR`.
2. Loader must expose settings for `HybridChunker` configuration (chunk tokenizer model, export type) while keeping those settings internal (derived from `CHUNK_SIZE`/`CHUNK_OVERLAP`).
3. Implement retry/backoff for download failures plus checksum validation; cache hits should skip re-downloads.
4. Preserve Docling metadata (page, header hierarchy, chunk ids) for downstream provenance.

### LR-CHUNK (Chunking & Splitting)
1. Replace the placeholder string slicing with the actual `docling.chunking.HybridChunker` output; fall back to `MarkdownHeaderTextSplitter` when `ExportType.MARKDOWN` is selected.
2. Honor `CHUNK_SIZE` / `CHUNK_OVERLAP` env values when configuring chunking behavior and log the effective size/overlap used.
3. Include metadata describing which chunking strategy produced each chunk (`doc_chunks`, `markdown_splitter`) for observability and validation.

### LR-EMBED (Embeddings)
1. Use `langchain_huggingface.embeddings.HuggingFaceEmbeddings` with `model_name="sentence-transformers/all-MiniLM-L6-v2"` and `cache_folder` rooted in `DOC_CACHE_DIR`.
2. Ensure embeddings run on CPU without tokens; if a token-less path fails, surface a clear warning but continue via fallback (hash/vector stub) so CLI can still run in constrained environments.
3. Emit metrics for embeddings count, latency, cache hits, and HuggingFace backend version; store them in `RunSummary.metrics["embedder"]`.
4. Provide `embed_query()` wrappers so `LangChain` retrievers receive consistent embeddings for both documents and queries.

### LR-STORE (Milvus Storage)
1. Replace the in-memory `MilvusStore` with `langchain_milvus.Milvus` (or `Milvus.from_documents`) configured via the resolved `MILVUS_URI` (auto-generated Lite path when blank) and `MILVUS_COLLECTION`.
2. Manage lifecycle for Milvus Lite directories inside `DOC_CACHE_DIR` (auto-create when `MILVUS_URI` blank, cleanup via teardown callbacks).
3. Surface index/collection metadata (dimension, index type, metric) inside `RunSummary.metrics["storage"]`.
4. When remote URIs are provided, enforce TLS/auth handling as described in `env_architecture.md` while keeping secrets internal.

### LR-RETRIEVE (LangChain Retrieval & LLM)
1. Instantiate `PromptTemplate` + `create_stuff_documents_chain` + `create_retrieval_chain` with the Milvus retriever (`vectorstore.as_retriever(search_kwargs={"k": settings.top_k})`).
2. Use `langchain_huggingface.HuggingFaceEndpoint` for answer generation with the `mistralai/Mistral-7B-Instruct-v0.2` repo id (default) and no token required; if HF throttles anonymous access, capture the warning/error and fall back to deterministic summarization so CLI logs still show an answer stub.
3. CLI output must match the original script (question banner, answer text, retrieved sources with metadata) while now reflecting real LangChain outputs.
4. Record retrieval latency, chain timings, and each source’s metadata (chunk id, score, page, section) for validation.

### LR-CONF (Configuration & CLI)
1. `pyrag.config.PipelineSettings` keeps the same nine env knobs; new LangChain-specific settings (prompt template, Docling export params, HF model ids) remain internal constants.
2. `.env.example`, CLI help, and README must only mention the nine env vars while clarifying that Docling/Milvus/HuggingFace dependencies are now active.
3. CLI must continue to support overrides via Typer options (already wired), display sanitized settings snapshots, and exit non-zero when real library initialization fails.

### LR-VAL (Validation & Telemetry)
1. `pyrag.validation.validate` must expand its checks to ensure real retrieval succeeded (e.g., search result includes `settings.top_k` hits when available, HuggingFaceEndpoint reported success) while still honoring the existing doc/chunk/embed constraints.
2. Metrics logged in each stage must enumerate the real backend names/versions so QA evidence proves LangChain/Docling/Milvus were exercised.

### LR-TEST (Testing & Offline Support)
1. Update `tests/test_modules.py` and `tests/test_pipeline.py` to detect when real dependencies are available vs. when fakes should be injected. Provide fixtures/fakes so CI can stub `DoclingLoader`, `Milvus`, and `HuggingFaceEndpoint` while the CLI/e2e tests still prove the wiring logic.
2. Ensure pytest can run entirely offline by default (e.g., guard heavy imports behind lazy loading, gate remote calls behind `PYRAG_TEST_MODE` or dependency-injection hooks).
3. Expand QA coverage to confirm `uv tool run ruff format`, `uv tool run ruff check`, `uv run --extra dev pytest output/42/tests`, and two `uv run pyrag` executions (default `.env` + inline overrides) succeed with the real libraries; document commands/timestamps/results in `lib_test_results.md`.

### LR-DOC (Documentation & Logs)
1. README + `.env.example` must be updated to describe the reinstated libraries, caching expectations, and fallback behavior.
2. `lib_build_log.md` must enumerate every command/file touched when introducing the real dependencies (pyproject/uv.lock adjustments, new cache directories, etc.).
3. `lib_docs.md` should summarize what changed for future reviewers once documentation refresh happens.

## Quality Attributes
- **Reliability**: Pipeline must fail fast with descriptive errors when Docling downloads fail, Milvus URIs are unreachable, or HuggingFaceEndpoint throttles requests; fallback summaries must keep CLI usable when the LLM is offline while still returning non-zero exit codes when critical stages fail.
- **Performance**: Default run should process the Docling PDF in under 2 minutes on a cold cache and subsequent runs should reuse cached Docling + embedding assets. Metrics must expose stage durations so regressions can be spotted.
- **Security**: No new env vars; `MILVUS_URI` redaction stays in place; HuggingFace tokens (when optionally configured for dev/testing) must never be logged.
- **Maintainability**: Keep modules protocol-based so future storage/retriever swaps require minimal changes; ensure real library usage is encapsulated per module.

## Testing & Validation Obligations
1. Minimum test coverage: module unit tests for loader/chunker/embedder/storage/search plus pipeline integration and CLI smoke tests must remain in `output/42/tests/`.
2. Tests must assert that the real library classes are imported/initialized (using monkeypatch/spies) so regressions that remove them are caught.
3. Automation must continue to enforce Ruff format/lint before pytest and CLI runs; command outputs, exit codes, and any warnings must be logged in `lib_test_results.md`.
4. When remote services are unavailable, document the observed behavior and remediation in the same log so defect triage (Feature 4 error-detective) has actionable data.

## Documentation & Developer Experience
- Provide onboarding notes in README describing how the Docling PDF is cached, how Milvus Lite directories are cleaned up, and what to expect from HuggingFaceEndpoint latencies.
- Document how to override `DOC_CACHE_DIR` or `MILVUS_URI` for local Milvus clusters without altering code.
- Clarify in docs that embeddings never require tokens but providing an HF token (via future secure store) may improve LLM answer quality—without reintroducing env vars.

## Acceptance Criteria
1. `uv run pyrag` executes the real Docling/LangChain pipeline, prints the same style of question/answer/sources as the reference script, and surfaces stage metrics proving each library ran.
2. Ruff format/check, pytest (with dependency injection), and two CLI runs pass without manual environment tweaks beyond the nine sanctioned variables.
3. README + `.env.example` + `lib_docs.md` reflect the new behavior and configuration expectations.
4. `lib_build_log.md` + `lib_test_results.md` capture reproducible evidence of the reinstated libraries working (commands, exit codes, timestamps, observed outputs).
5. All new requirements remain within the nine-variable contract and keep Feature 3 validation rules intact.

## Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Heavy dependencies (Docling, LangChain, Milvus, HuggingFace) slow CI | Timeouts / flaky tests | Cache downloads in `DOC_CACHE_DIR`, provide fake implementations for tests, document cache warm-up steps. |
| Milvus Lite incompatibility on certain systems | Pipeline crashes early | Add pre-flight check/logging for `MILVUS_URI`, allow overriding via env, and ensure teardown cleans hidden directories. |
| HuggingFaceEndpoint throttles anonymous requests | Answer step fails despite retrieval success | Implement fallback summary + warning, provide hook for optional token injection without exposing a new env var. |
| Network outages when downloading Docling PDF | Loader fails | Cache the PDF, allow offline runs using cached copy, surface remediation instructions in CLI/logs. |
| Future contributors reintroduce extra env vars | Configuration drift | Enforce config gating in `pyrag/config.py` (ignore unknown keys), update docs/tests to fail if unauthorized envs are consumed. |

These requirements now define the scope and guardrails for re-adding the real LangChain Docling RAG stack so subsequent architecture, design, implementation, and QA tasks can proceed with confidence.
