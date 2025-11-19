# UV Packaging Architecture

## Context Recap
- Goal: encapsulate the Docling-driven LangChain RAG workflow into a UV-managed CLI invoked solely as `uv run pyrag`.
- Reference requirements: modular loader → chunker → embedder → storage → search pipeline, HuggingFace-token-free embeddings via `sentence-transformers/all-MiniLM-L6-v2`, and deterministic lint/test tooling (`uv ruff format`, `uv ruff check`).
- API designer focus: define predictable boundaries between CLI, orchestration, and modules so later engineers can implement without diverging from the spec.

## Target UV Project Layout
```
repo-root/
├── pyproject.toml            # UV-managed metadata + scripts (format, lint, run)
├── uv.lock                   # Frozen dependency graph
├── README.md                 # Run instructions & prerequisites
├── .env.example              # Optional user overrides (HF_TOKEN, MILVUS_URI, QUERY_TEXT)
├── pyrag/
│   ├── __init__.py
│   ├── __main__.py          # Thin shim: calls pyrag.cli.main()
│   ├── cli.py               # Click/Typer CLI exposing `pyrag` command
│   ├── config.py            # `.env` + defaults loader (python-dotenv)
│   ├── pipeline.py          # High-level orchestrator wiring modules
│   ├── logging.py           # Shared logging helpers (optional but recommended)
│   ├── loader.py            # Docling ingestion abstraction
│   ├── chunker.py           # LangChain text splitters (Docling chunk metadata aware)
│   ├── embedder.py          # Sentence-transformers wrapper
│   ├── storage.py           # Milvus / vector store glue
│   ├── search.py            # Retrieval + response formatting
│   └── validation.py        # Lightweight smoke validation invoked post-run
└── tests/
    └── test_pipeline.py     # Placeholder for validation automation
```

## Entry Point Flow
1. **UV** resolves the project virtual environment and dependencies via `pyproject.toml` + `uv.lock`.
2. `uv run pyrag` executes the `pyrag` console script mapped to `pyrag.__main__:main` (or `[tool.uv.scripts] pyrag = "pyrag"`).
3. `pyrag/__main__.py` imports `pyrag.cli.main()` to avoid duplicated bootstrapping logic.
4. `pyrag.cli` boots Typer/Click CLI, auto-loads `.env` through `pyrag.config`, and constructs a `PipelineSettings` dataclass capturing loader/chunker/embedder/storage/search knobs.
5. CLI calls `pyrag.pipeline.run(settings)` which:
   - Initializes logging and telemetry (stdout for now).
   - Instantiates module classes (e.g., `DoclingLoader`, `MarkdownChunker`, `MiniL6Embedder`, `MilvusVectorStore`, `LangChainRetriever`).
   - Streams progress events (loading, chunking, embedding, storing, querying, result formatting) back to CLI for user feedback.
6. `pyrag.validation.validate(settings, run_summary)` executes simple assertions (non-empty docs, embeddings count matches chunk count, search returns ≥1 hit) and surfaces failures with actionable errors.

## Module Responsibilities & Interfaces
- `loader.LoaderProtocol`: exposes `load() -> list[DocChunk]` using Docling ingestion; configurations from `.env` such as `SOURCE_URL`.
- `chunker.ChunkerProtocol`: `chunk(docs) -> list[Chunk]` with Docling metadata preserved for provenance.
- `embedder.EmbedderProtocol`: wraps `sentence-transformers/all-MiniLM-L6-v2`; ensures offline-friendly download and CPU inference fallback; interface `embed(chunks) -> list[Embedding]`.
- `storage.StorageProtocol`: manages Milvus (or Milvus Lite) session lifecycle; interface `persist(embeddings) -> StorageHandle` and `query(StorageHandle, query_text, top_k)`.
- `search.SearchOrchestrator`: uses LangChain retriever to combine storage handle, embedder, and optional re-ranker; returns structured `SearchResult` objects consumed by CLI for printing/logging.
- `config.PipelineSettings`: dataclass capturing defaults (document URL, chunk size, embedding model, Milvus URI). `.env` overrides are loaded at CLI start; missing values fall back to deterministic defaults so `HF_TOKEN` is optional.

Each module exposes explicit types to keep the API surface self-documenting and to ease future unit tests.

## Configuration & `.env` Handling
- `.env.example` lists optional keys: `SOURCE_URL`, `DOC_CACHE_DIR`, `MILVUS_URI`, `MILVUS_COLLECTION`, `QUERY_TEXT`, `HF_TOKEN` (optional).
- `pyrag.config` loads `.env` via `python-dotenv` before CLI parsing. Missing `.env` simply yields default settings defined inside `PipelineSettings`.
- CLI logs a warning (not error) when `HF_TOKEN` is absent; embedder internally configures `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", use_auth_token=None)` to avoid authentication.
- Temporary directories (e.g., for Milvus Lite or Docling export) are created with `tempfile.TemporaryDirectory()` within `storage` to avoid manual setup.

## Dependency Graphs
**Runtime call graph** (textual):
```
uv run pyrag
  ↓ uv launcher
pyproject.toml → [tool.uv.scripts].pyrag
  ↓ console script
pyrag.__main__.main()
  ↓ CLI wiring
pyrag.cli.main()
  ↓ configuration
pyrag.config.load_settings()
  ↓ orchestration
pyrag.pipeline.run(settings)
      ↙        ↓         ↘
 loader   chunker    embedder
      ↓        ↘         ↓
   documents   chunks → embeddings
                      ↓
                   storage
                      ↓
                    search
                      ↓
                validation
```

**Module dependency matrix**:
- `cli` depends on `config`, `pipeline`.
- `pipeline` depends on `loader`, `chunker`, `embedder`, `storage`, `search`, `validation`, `logging`.
- `loader` depends on `docling`, `langchain-docling`.
- `chunker` depends on `langchain-text-splitters`, `docling` models.
- `embedder` depends on `sentence-transformers`, `torch/onnxruntime` (CPU-compatible).
- `storage` depends on `langchain-milvus`, `pymilvus`, and uses temporary filesystem utilities.
- `search` depends on `langchain`, `langchain-core`, `langchain-huggingface` (only if re-ranking) but not on `.env`.
- `validation` depends on `pipeline` data classes only; no external libs.

## Deterministic CLI Contract
- `pyproject.toml` defines `[project.scripts] pyrag = "pyrag.__main__:main"` so UV installs a console entry point, enabling `uv run pyrag` and (optionally) `uv tool install . && pyrag`.
- `[tool.uv.scripts]` mirrors the console entry to allow `uv run pyrag` without `python -m` boilerplate.
- Lint/test automation is expressed via `[tool.uv.scripts] format = "ruff format ."`, `lint = "ruff check ."`, and `validate = "pyrag"` to keep commands single-source.

## Artifact Interfaces for Downstream Stages
- **`uv_design.md` seed inputs**: pyproject script declarations, directory skeleton, module protocol names, config keys, validation expectations.
- **Implementation guards**: CLI must call `validation` before exiting to ensure acceptance criteria around demonstration evidence.
- **Testing hooks**: `tests/test_pipeline.py` should import `pyrag.pipeline` and use `PipelineSettings` fixtures to assert loader/chunker/embedder contract compliance.

This architecture ensures every subsequent phase (design, build, validation) inherits a deterministic, modular, and developer-friendly blueprint centered on the singular `uv run pyrag` experience.
