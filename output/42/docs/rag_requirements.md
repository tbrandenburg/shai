# Feature 2 – Modular RAG Requirements

## Objective
- Repackage the Docling + LangChain prototype into a UV-managed, modular pipeline where `uv run pyrag` remains the only public entrypoint while the loader → chunker → embedder → storage → search stages become discrete, testable modules.
- Preserve the functional behavior of the original script (Docling Technical Report ingestion, MiniLM embeddings, Milvus-backed retrieval, question answering) while improving maintainability, validation coverage, and clarity for downstream architects.

## Source Inputs
- Issue #42 request (see `issue_conversation.md` and `issue_context.json`).
- UV architecture contract documented in `uv_architecture.md`.
- Feature 1 deliverables (`uv_requirements.md`, `uv_architecture.md`, `uv_design.md`) that already define packaging, CLI, and validation expectations for Feature 2 to inherit.

## Stakeholders & Users
- **Primary user**: CLI operators who need a deterministic `uv run pyrag` experience without environment tweaking.
- **Engineering stakeholders**: data/LLM engineers implementing modules, QA/test automation ensuring regressions surface quickly, and project leadership who need evidence that the RAG flow still answers the baseline Docling question.

## Business Goals & KPIs
1. **Single-command UX**: 100% of supported workflows must succeed via `uv run pyrag` with default settings.
2. **Modularity**: Each RAG stage exposes a protocol/dataclass contract so design/QA can test components in isolation; traceability maintained between requirements and code modules listed in `uv_architecture.md`.
3. **Token-free embeddings**: 0 reliance on HuggingFace auth for `sentence-transformers/all-MiniLM-L6-v2`; warnings allowed for optional HF token used by the LLM, but embeddings must run offline.
4. **Validation coverage**: Smoke validation proves at least one retrieval hit for the default query and surfaces counts for docs, chunks, embeddings, and results.
5. **Compliance**: Code remains PEP8-compliant, `uv ruff format` and `uv ruff check` clean, and module boundaries align with the architecture blueprint.

## Constraints & Assumptions
- Python 3.11 project managed by UV; dependencies resolved through `pyproject.toml` + `uv.lock` only.
- CLI must auto-load `.env` (if present) but ship sensible defaults; optional values like `HF_TOKEN` never block execution.
- Storage relies on Milvus (preferred Milvus Lite/file-backed path) spun up automatically; no external services mandated for default mode.
- No new user-facing features or configuration flags beyond those required to express the modular structure.
- Logging/telemetry remains console-based (stdout) and mirrors the five main phases from the original script.
- Tests must be runnable without network access beyond downloading the public Docling PDF and HuggingFace MiniLM weights.

## Functional Requirements
### 1. CLI & Pipeline Orchestrator
- **FR-O1**: `pyrag.cli` exposes a Typer (or equivalent) command registered under `[project.scripts]` and `[tool.uv.scripts]` so `uv run pyrag` calls `pyrag.cli.main()`.
- **FR-O2**: CLI loads `.env`, constructs a `PipelineSettings` dataclass, and logs each phase boundary (load, chunk, embed, index, query, validation) with human-readable timestamps.
- **FR-O3**: `pyrag.pipeline.run(settings)` orchestrates modules through dependency-injected interfaces and returns a `RunSummary` capturing key counts, query text, and retrieved sources for validation/reporting.
- **FR-O4**: Orchestrator must raise actionable exceptions when any module reports zero output (e.g., 0 chunks, 0 embeddings) and must fail fast before search to keep the CLI contract deterministic.

### 2. Loader Module (`pyrag/loader.py`)
- **FR-L1**: Provide a `LoaderProtocol` with `load(settings: PipelineSettings) -> list[DocChunk]` implemented via `DoclingLoader` configured for the default Docling Technical Report URL.
- **FR-L2**: Loader must allow switching between `ExportType.DOC_CHUNKS` and `ExportType.MARKDOWN` via configuration but ship with DOC_CHUNKS default to match the baseline script.
- **FR-L3**: Preserve Docling metadata (source path, page ranges, headers) for downstream provenance tracking; metadata must survive through chunking and storage.
- **FR-L4**: Implement retry or clear error handling for network/download failures, emitting user-facing messages that point to `SOURCE_URL` overrides without requiring manual edits to the code.

### 3. Chunker Module (`pyrag/chunker.py`)
- **FR-C1**: Accept Docling documents and output normalized `Chunk` objects with fields `(text, metadata, ordering_index)`; metadata must include document id, section headers, and token counts.
- **FR-C2**: Provide default chunking strategy aligned with `HybridChunker` semantics (Docling chunk metadata). If fallback splitting occurs (e.g., Markdown splitter), record the mode in metadata for observability.
- **FR-C3**: Pipeline settings must capture chunk size, chunk overlap, and headers-to-track; chunker enforces those values to keep validation deterministic.
- **FR-C4**: Chunking step must report its totals (chunks produced, median length) to the CLI/pipeline summary.

### 4. Embedder Module (`pyrag/embedder.py`)
- **FR-E1**: Wrap `sentence-transformers/all-MiniLM-L6-v2` using `SentenceTransformer(..., use_auth_token=None)`; warn (but do not fail) if `HF_TOKEN` missing when other models require it.
- **FR-E2**: Provide `embed(chunks: Sequence[Chunk]) -> list[Embedding]` returning both vector arrays and chunk ids for storage alignment.
- **FR-E3**: Support CPU-only environments; any GPU detection must default gracefully to CPU.
- **FR-E4**: Cache the model within the UV virtual environment so repeated runs avoid re-downloading weights.
- **FR-E5**: Emit metrics: number of embeddings created, latency per 100 chunks, and whether cached weights were used.

### 5. Storage Module (`pyrag/storage.py`)
- **FR-S1**: Manage Milvus (lite/file-backed) lifecycle internally; default to `tempfile.TemporaryDirectory()` + file URI (`milvus_uri`) when `.env` doesn’t specify an external endpoint.
- **FR-S2**: Provide `persist(embeddings: list[Embedding], settings) -> StorageHandle` that builds/updates a collection named by configuration (default `docling_demo`).
- **FR-S3**: Provide `query(handle: StorageHandle, query: str, top_k: int) -> list[RetrievedDocument]` that uses the embedder for query vectors and respects `settings.top_k` (default 5).
- **FR-S4**: Expose cleanup/teardown hooks so tests can dispose of local Milvus artifacts; CLI should call these hooks after validation.
- **FR-S5**: Record index parameters (e.g., `index_type=FLAT`) and collection stats so QA can verify parity with the original script.

### 6. Search Module (`pyrag/search.py`)
- **FR-R1**: Use LangChain retrieval utilities (`create_stuff_documents_chain` + `create_retrieval_chain`) to combine Milvus retriever and prompt template identical to the original script.
- **FR-R2**: Accept the question from settings (default "Which are the main AI models in Docling?") and allow overrides through `.env` without new CLI arguments.
- **FR-R3**: Return structured `SearchResult` entries containing answer text, confidence/score, and the clipped source metadata printed to stdout.
- **FR-R4**: Ensure the CLI prints both the final answer and each retrieved source snippet in the same format as Issue #42’s script (question, answer, retrieved sources list).

### 7. Validation Module (`pyrag/validation.py`)
- **FR-V1**: Implement `validate(run_summary: RunSummary) -> None` that enforces: ≥1 document, ≥1 chunk, embeddings count == chunk count, `top_k` hits returned, and answer text non-empty.
- **FR-V2**: Provide structured error messages that the CLI can surface; include remediation tips (e.g., "Set SOURCE_URL to reachable PDF").
- **FR-V3**: Validation output must be appended to CLI logs and recorded inside `uv_test_results.md` or future `rag_test_results.md` by QA phases.

### 8. Configuration & Environment (`pyrag/config.py`, `.env.example`)
- **FR-G1**: Define `PipelineSettings` capturing: `source_url`, `export_type`, `doc_cache_dir`, `chunk_size`, `chunk_overlap`, `milvus_uri`, `milvus_collection`, `query_text`, `top_k`, `hf_token`, `log_level`.
- **FR-G2**: `load_settings()` reads `.env`, applies defaults, and validates invariants (positive chunk size, 0 ≤ overlap < size, `top_k` ≥ 1).
- **FR-G3**: `.env.example` must enumerate every configurable value with sample defaults plus comments describing when to tweak each.
- **FR-G4**: Settings object must be serializable/loggable so downstream components (design, QA) can snapshot the run configuration.

### 9. Testing & Observability
- **FR-T1**: Provide fixtures/mocks so `tests/test_pipeline.py` can run without contacting Milvus/network by injecting fake loader/storage implementations.
- **FR-T2**: Document how QA should measure run success (commands, expected CLI excerpts) within `rag_test_results.md` once available.
- **FR-T3**: CLI should expose a verbose flag placeholder (even if not wired yet) to future-proof richer telemetry without breaking the single-command contract.

## Interfaces & Data Contracts
| Artifact | Fields | Notes |
| --- | --- | --- |
| `PipelineSettings` | Values listed in FR-G1 | Single source of truth loaded before pipeline starts. |
| `DocChunk` | `id`, `text`, `metadata`, `tokens` | Output of loader when EXPORT_TYPE = DOC_CHUNKS. |
| `Chunk` | `id`, `text`, `metadata`, `order_index` | Chunker-normalized representation consumed by embedder. |
| `Embedding` | `id`, `vector`, `metadata` | Embeddings align 1:1 with `Chunk`. |
| `StorageHandle` | `collection_name`, `connection_args`, `metadata` | Allows search module to reuse connections without reinitializing Milvus. |
| `SearchResult` | `question`, `answer`, `sources`, `latency_ms`, `top_k` | Returned to CLI for printing and to validation for scoring. |
| `RunSummary` | `documents`, `chunks`, `embeddings`, `results`, `settings_snapshot` | Drives validation and QA evidence.

## Dependencies & External Services
- Docling + LangChain packages listed in `uv_design.md` with emphasis on `docling`, `langchain-docling`, `langchain-text-splitters`, `langchain-milvus`, `langchain-huggingface`, `sentence-transformers`, `pymilvus`, `milvus-lite`, `python-dotenv`, `typer`, `rich`.
- Storage default is Milvus Lite (file-backed). When `MILVUS_URI` points at a remote cluster, TLS/auth configuration must be accepted from `.env` but not required for default mode.
- Optional HuggingFace generation endpoint still references `mistralai/Mistral-7B-Instruct-v0.2`; if tokens absent, CLI should warn yet continue (answer quality may degrade but pipeline must run).

## Validation Metrics & Reporting
- **Loader metrics**: documents downloaded, document sizes, elapsed time.
- **Chunker metrics**: chunk count, average tokens per chunk, chunking mode (Doc chunks vs Markdown).
- **Embedder metrics**: embeddings count, total embedding time, whether model cache hit.
- **Storage metrics**: collection name, vector dimensionality, Milvus URI, index type.
- **Search metrics**: `top_k`, answer latency, confidence scores per result.
- **Validation metrics**: boolean success flag, failure reasons, summary of retrieved source titles.
- QA must capture these metrics in `rag_test_results.md` along with command outputs to prove the modular pipeline still mirrors the original script.

## Risks & Mitigations
- **Model download latency**: Document first-run time and encourage prefetch via `uv run pyrag --prefetch` (future) or manual `sentence-transformers` cache warm-up.
- **Milvus resource usage**: Provide clear cleanup hooks to prevent temp directory bloat; recommend `MILVUS_URI` override for CI caching.
- **Docling data drift**: If the source PDF moves or changes, allow `SOURCE_URL` override and log checksum mismatch warnings.
- **HF token confusion**: Warn users that embeddings never need a token; README + CLI messaging should differentiate between optional generation tokens and default token-free behavior.

## Acceptance Criteria
1. `uv run pyrag` runs the modular pipeline end-to-end using the Docling Technical Report and prints the same question/answer/source summary as the original script.
2. Each module exposes documented interfaces described above, and code files line up with the blueprint in `uv_architecture.md`.
3. Embeddings leverage `sentence-transformers/all-MiniLM-L6-v2` without requiring a HuggingFace token; CLI warns—but does not crash—when the user lacks `HF_TOKEN`.
4. Validation step enforces data-integrity checks and fails the command when expectations are not met.
5. Metrics for each stage are logged and can be referenced later inside `rag_test_results.md`.
6. Documentation (`README`, `.env.example`) reflects every configuration knob introduced by Feature 2.

## Traceability
- Requirements trace back to Issue #42 directives and architecture plan rows where loader/chunker/embedder/storage/search responsibilities were defined.
- Future architecture (`rag_architecture.md`), design (`rag_design.md`), implementation, and QA artifacts must reference this document to show coverage for each requirement ID (FR-*).
