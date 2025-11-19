# Feature 1 – Technical Design (Backend Engineer)

## 1. Package & Module Layout
| Path | Purpose | Key Functions/Classes |
| --- | --- | --- |
| `pyrag/__init__.py` | Declare package exports; expose `__all__` for CLI/runtime helpers. | `__version__` constant read from `pyproject.toml`. |
| `pyrag/__main__.py` | Typer-based CLI entrypoint executed via `uv run pyrag`. Handles argument parsing, dependency wiring, and orchestrates the pipeline. | `cli()` root command; `run_pipeline(pdf_path, query, **options)` thin wrapper over `pipeline.execute`. |
| `pyrag/config.py` | Centralized defaults + validation utilities shared across modules. Converts CLI/env/pyproject values into a dataclass consumed by the pipeline. | `PipelineConfig` dataclass; `load_config(cli_args)` factory; `resolve_cache_paths()` helper. |
| `pyrag/logging.py` | Structured logging primitives so all modules emit consistent context-aware diagnostics. | `configure_logging(verbosity)`; `log_stage(stage, event, **metadata)` for structured events. |
| `pyrag/doc_loader.py` | Document ingestion adapters (Docling primary, PyPDF fallback). | `load_pdf(path: Path, metadata_only=False)`; raises `DocumentLoadError`. |
| `pyrag/chunker.py` | Text chunking using LangChain splitters with deterministic parameters. | `chunk_documents(documents, chunk_size, chunk_overlap)` returning list of `Document`. |
| `pyrag/embed.py` | Embedding factory returning a LangChain embedding object without remote tokens. | `build_embeddings(model_name, cache_dir)` with fallback order. |
| `pyrag/vectorstore.py` | Vector store abstraction over FAISS with optional persistence. | `build_vectorstore(embeddings, documents, persist_path=None)`; `get_retriever(store, k, score_threshold)`. |
| `pyrag/pipeline.py` | Orchestrates ingestion → chunking → embeddings → retrieval → answer synthesis/fallback generation. Encapsulates LangChain chain wiring. | `execute(config: PipelineConfig)` raising typed exceptions; `format_answer(result)` helper. |
| `tests/` | Pytest suites plus fixtures for dummy PDF validation. | `tests/fixtures/dummy.pdf`; `tests/test_pipeline.py`. |

## 2. Control & Data Flow
1. `__main__.py` parses CLI args (`--pdf`, `--query`, `--chunk-size`, `--chunk-overlap`, `--embedding-model`, `--k`, `--persist`, `--verbose`, `--retriever-backend`, `--llm-backend`).
2. Args feed `config.load_config`, which resolves cache dirs (default `.uv-cache/pyrag/`), merges env vars (e.g., `PYRAG_MODEL_PATH`), and validates file existence.
3. `pipeline.execute` receives `PipelineConfig`, initializes logging once, and instantiates stage objects lazily per config.
4. Stages run sequentially:
   - `doc_loader.load_pdf` returns LangChain `Document` list with metadata.
   - `chunker.chunk_documents` splits text; optional serialization via `config.cache_chunks_path` when `--persist-chunks` true.
   - `embed.build_embeddings` downloads (if missing) the configured SentenceTransformer into uv cache; returns embedding callable.
   - `vectorstore.build_vectorstore` indexes chunks via FAISS (default) or Chroma fallback; persists to `/tmp/pyrag_index.faiss` when `--persist-index` true.
   - `pipeline.execute` builds a retrieval QA chain: prefer `langchain.chains.RetrievalQA` with `llm=LlamaCpp` or `GPT4All` referencing local weights defined in config; fallback to concatenated context summary when no local LLM is configured.
5. `pipeline.format_answer` enriches output with cited metadata, prints to stdout, optionally writes JSON when `--output-json` provided (future extension stub).

## 3. Configuration Surface
| Source | Option | Default | Notes |
| --- | --- | --- | --- |
| CLI / env | `--pdf / PYRAG_PDF_PATH` | `tests/fixtures/dummy.pdf` | Must exist/readable; validated in `config.load_config`. |
| CLI | `--query` | _required_ | Non-empty string; consider quoting in shell. |
| CLI | `--chunk-size` | `750` | Passed to `RecursiveCharacterTextSplitter`. |
| CLI | `--chunk-overlap` | `100` | Same as above. |
| CLI | `--embedding-model / PYRAG_EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local model path cached under uv-managed dir. |
| CLI | `--k` | `4` | Number of retrieved docs. |
| CLI | `--persist-index` | `False` | When true, writes FAISS index to `/tmp/pyrag_index.faiss`. |
| CLI | `--persist-chunks` | `False` | When true, writes chunk JSON to `.uv-cache/pyrag/chunks.json`. |
| CLI | `--retriever-backend` | `faiss` | Fallback `chroma`. |
| CLI | `--llm-backend` | `llama_cpp` | Options: `gpt4all`, `context-only`. |
| CLI | `--verbose / -v` | INFO default, DEBUG when flagged | Drives logging verbosity. |
| Pyproject `[project.scripts]` | `pyrag = pyrag.__main__:cli` | Required for `uv run pyrag`. |
| Pyproject `[project.dependencies]` | langchain, docling, sentence-transformers, faiss-cpu, llama-cpp-python (or gpt4all), typer, pydantic, loguru | Keep <= required minimal set. |

`config.PipelineConfig` also captures: `cache_dir`, `model_local_path`, `vectorstore_path`, `chunk_cache_path`, `timeout_seconds`, and `dry_run` flag (for tests).

## 4. Logging & Observability
- Initialize via `logging.configure_logging(verbosity)` inside `__main__.py`; default formatter: `[%(levelname)s] %(asctime)s %(stage)s %(message)s` with optional JSON when `PYRAG_LOG_JSON=1`.
- Each stage calls `log_stage(stage_name, event="start"|"end", duration_ms, details={...})`.
- Log success + failure of external dependencies (Docling parse, embedding download) with hashed artifact paths for traceability.
- Emit summary block at end containing number of chunks, retrieval latency, answer length, and fallback mode indicator.
- Provide `--log-file path` (optional) to duplicate logs via `logging.FileHandler` for QA ingestion.

## 5. Error Handling & Resilience
| Failure | Detection | Response |
| --- | --- | --- |
| Missing PDF / unreadable | `config.load_config` and `doc_loader.load_pdf` check `Path.is_file()` and catch Docling exceptions. | Raise `InvalidInputError` with actionable hint; CLI catches and exits code 2. |
| Docling parse failure | Catch `DoclingError`. | Retry w/ PyPDFLoader fallback; log warning referencing fallback path. |
| Embedding model unavailable offline | `embed.build_embeddings` wraps LangChain `HuggingFaceEmbeddings` instantiation. | Attempt fallback model (`paraphrase-MiniLM-L3-v2`), warn user; final failure raises `EmbeddingInitError`. |
| Vector store init failure | Wrap FAISS creation in try/except. | Switch to Chroma in-memory backend, log info; escalate if both fail. |
| LLM weights missing | `pipeline.execute` checks local file path before instantiation. | If not found and no `OPENAI_API_KEY`, degrade to `context-only` summarizer with deterministic template; log degrade flag. |
| Runtime exceptions | Use `try/except Exception as exc` around pipeline; log stack trace at DEBUG and return exit code 1 with short message. |

## 6. File & Dependency References
- `pyrag/__main__.py`: CLI + logging init; depends on Typer + config/pipeline modules.
- `pyrag/pipeline.py`: Imports `doc_loader`, `chunker`, `embed`, `vectorstore`, LangChain chains, and offline LLM wrappers.
- `pyproject.toml`: under `[project]` include dependencies plus `[tool.uv]` metadata. Add `[tool.uv.sources]` if need to reference local packages. Keep extras minimal for offline install.
- `uv.lock`: generated by `uv lock`; check in for reproducibility.
- Tests reference `tests/fixtures/dummy.pdf`; ensure fixture copied into repo root for offline execution.

## 7. Open Questions / Assumptions
1. Offline LLM choice: default to `llama-cpp-python` with `ggml-model-q4_0.bin` (~3.9 GB). If repo size constraints disallow storing weights, document manual download path and rely on `context-only` fallback until QA approves a smaller GPT4All model.
2. Persistence strategy: initial scope only caches on-disk when flags enabled; no long-term vector DB. Future work may add `--persist <dir>` CLI.
3. Security: No auth because single-user CLI; still sanitize file paths and avoid network I/O beyond initial model download.

This design aligns with the architecture blueprint while giving python implementation teams concrete files, interfaces, and operational touchpoints.
