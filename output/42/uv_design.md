# UV Packaging Design

## Implementation Overview
- Convert the Docling-driven LangChain prototype into a UV-managed Python 3.11 project whose only public entrypoint is `uv run pyrag`.
- Preserve the architecture contract from `uv_architecture.md`: CLI → config → pipeline orchestrator → loader → chunker → embedder → storage → search → validation.
- Produce deterministic tooling by codifying lint/test commands in `pyproject.toml` and mirroring them under `[tool.uv.scripts]`.
- Provide scaffolding files up front so downstream contributors only fill in business logic rather than worrying about packaging decisions.

## `pyproject.toml` Specification
### Build System & Project Metadata
| Field | Value |
| --- | --- |
| `[build-system]` | `requires = ["setuptools>=69", "wheel"]`, `build-backend = "setuptools.build_meta"` |
| `[project]` | `name = "pyrag"`, `version = "0.1.0"`, `description = "Docling-powered modular RAG CLI"`, `readme = "README.md"`, `requires-python = ">=3.11"`, `license = {text = "Apache-2.0"}` |
| `authors` | `[{ name = "SHAI", email = "ops@shai.dev" }]` |
| `dependencies` | Listed in Runtime Dependencies below |
| `[project.optional-dependencies]` | `dev = ["pytest==8.3.3", "pytest-mock==3.14.0"]` |
| `[project.urls]` | `"Source" = "https://github.com/.../shai"` (update with real repo URL) |

### Runtime Dependency Pins (initial targets)
| Package | Purpose |
| --- | --- |
| `langchain==0.3.0` | Orchestrates RAG components |
| `langchain-core==0.3.0` | Shared abstractions |
| `langchain-community==0.3.0` | Provides Docling + retriever integrations |
| `langchain-text-splitters==0.2.2` | Chunking utilities |
| `langchain-huggingface==0.1.2` | Optional rerankers/embedders |
| `langchain-milvus==0.1.3` | Storage adapter |
| `docling==2.4.0` | Document loader |
| `sentence-transformers==3.0.1` | `all-MiniLM-L6-v2` embeddings (token-free) |
| `torch==2.4.0` | Backend for embeddings (CPU build) |
| `onnxruntime==1.18.0` | Lightweight inference fallback |
| `pymilvus==2.4.3` | Milvus/Milvus Lite connectivity |
| `milvus-lite==2.4.7` | Embedded Milvus runtime (optional installation) |
| `python-dotenv==1.0.1` | `.env` handling |
| `typer==0.12.5` | CLI layer |
| `rich==13.9.1` | Console progress feedback |

> Use `uv add <pkg>==<version>` in the implementation phase to guarantee lock determinism. Adjust pins if UV reports incompatibilities, but record the final versions in `uv_build_log.md`.

### Development Tooling
- `ruff==0.6.3` (shared via `[project.optional-dependencies].dev` or `[tool.uv.dependencies.dev]`).
- `[tool.ruff]` config block: `line-length = 100`, `target-version = "py311"`, `lint.select = ["E", "F", "I", "B", "UP"]`.
- `[tool.ruff.format]` uses default settings to stay compatible with `uv ruff format`.

### Scripts & Entrypoints
```
[project.scripts]
pyrag = "pyrag.__main__:main"

[tool.uv.scripts]
pyrag = "pyrag"
format = "ruff format ."
lint = "ruff check ."
test = "pytest"
validate = "pyrag"
```
- `uv run pyrag` resolves to `[tool.uv.scripts].pyrag`.
- `uv run format|lint|test|validate` provide canonical automation hooks for CI.

### Lockfile Discipline
1. `uv lock --locked` (fails if lock stale) runs in CI.
2. Regeneration: `uv lock --upgrade` followed by `uv run lint` and `uv run test`.
3. Document each regen in `uv_build_log.md` with reasoning (e.g., CVE patch, dependency drift).

## Package Layout & Implementation Steps
1. **Bootstrap package**
   - `uv init --package pyrag` (or manual folder creation) ensures `pyrag/__init__.py` exists.
   - Create `pyrag/__main__.py` with `from .cli import main; if __name__ == "__main__": main()`.
2. **CLI (`pyrag/cli.py`)**
   - Implement a Typer app exposing a single `run` command invoked by default.
   - Load `.env` via `pyrag.config.load_settings()` before instantiating the pipeline.
   - Log phase transitions with `rich.console.Console` for readability.
3. **Config (`pyrag/config.py`)**
   - Define `PipelineSettings` dataclass: `source_url`, `output_dir`, `chunk_size`, `chunk_overlap`, `milvus_uri`, `milvus_collection`, `query_text`, `hf_token` (optional), `top_k`.
   - Provide `load_settings()` that merges defaults, `.env`, and CLI overrides (if ever added) and validates invariants.
4. **Pipeline (`pyrag/pipeline.py`)**
   - `run(settings: PipelineSettings) -> RunSummary` orchestrates loader→chunker→embedder→storage→search.
   - Keep modules decoupled via protocol/base classes placed next to each implementation for clarity.
5. **Modules**
   - `loader.py`: wrap Docling ingestion; expose `DoclingLoader(settings).load() -> list[DocDocument]`.
   - `chunker.py`: configure `RecursiveCharacterTextSplitter` with doc metadata.
   - `embedder.py`: instantiate `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu", use_auth_token=None)`; cache models in UV venv.
   - `storage.py`: spin up Milvus Lite via `milvus_lite.MilvusLite` if `MILVUS_URI` missing; maintain context manager for cleanup.
   - `search.py`: build LangChain `VectorStoreRetriever` using Milvus collection and embedder for queries.
   - `validation.py`: assert counts (docs, chunks, embeddings) and ensure at least one retrieval hit; raise `ValidationError` with actionable text.
   - `logging.py` (optional): centralize log configuration to avoid duplication (structured JSON ready).
6. **Tests (`tests/test_pipeline.py`)**
   - Add fixtures for `PipelineSettings` with mocked loader/embedder to avoid heavy downloads.
   - Provide smoke test verifying `pipeline.run` returns `RunSummary` with non-empty retrievals.

## Configuration Artifacts
- `.env.example` keys: `SOURCE_URL`, `DOC_CACHE_DIR`, `MILVUS_URI`, `MILVUS_COLLECTION`, `QUERY_TEXT`, `TOP_K`, `HF_TOKEN` (optional), `LOG_LEVEL`.
- README updates: describe UV installation, `uv sync`, `uv run pyrag`, expected logs, and troubleshooting tips (Milvus ports, model download speed).
- Mention that `.env` is optional; defaults live in `pyrag.config.DEFAULT_SETTINGS`.

## Validation & Tooling Flow
1. `uv sync` – create environment from lock.
2. `uv run format` – enforce consistent style.
3. `uv run lint` – static analysis gate.
4. `uv run test` – execute `pytest` suite (initially smoke test stub).
5. `uv run pyrag` – human-visible validation output.
6. Capture outputs in `output/42/uv_test_results.md` during later phases.

## Scaffolding Checklist
- [ ] Generate `pyproject.toml` per spec above.
- [ ] Run `uv add` for each dependency; commit resulting `uv.lock`.
- [ ] Create `pyrag/` package with modules and placeholder implementations.
- [ ] Add `.env.example` and README sections describing config + commands.
- [ ] Write `tests/test_pipeline.py` stub using pytest + fixtures.
- [ ] Verify `uv run pyrag` succeeds using stubbed pipeline before integrating real Docling/Milvus logic.

Delivering the above design gives the implementation phase an unambiguous blueprint for UV packaging, dependency governance, and CLI ergonomics.
