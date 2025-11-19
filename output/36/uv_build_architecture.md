# UV Project Architecture — `docling-milvus-rag`

## 1. Objective & Scope
The build system must guarantee that `uv run docling-milvus-rag` delivers the Docling→Milvus pipeline offline, in alignment with the CLI requirements brief. This document defines how UV manages the workspace layout, dependency graph, scripts, and reproducibility controls so subsequent CLI work can plug directly into the backend modules under `src/docling_milvus_rag/`.

## 2. Workspace Layout & Artifact Ownership
- **Root manifest**: `pyproject.toml` (Hatchling backend) + `uv.lock` are the single sources of truth; `pyproject.toml` stays human-maintained while `uv.lock` is regenerated via `uv lock --locked` when dependencies change.
- **Source tree**: `src/docling_milvus_rag/` contains the modular pipeline described in `rag_module_design.md` (config, loaders, chunking, embeddings, Milvus store, retrieval, LLM, pipeline orchestrator). CLI code (`cli.py`, optional `__main__.py`) will live here so UV’s editable install exposes it.
- **Configuration assets**: `config/defaults.toml` seeds runtime defaults; CLI/environment overrides cascade on top via Pydantic settings.
- **Runtime fixtures**: `fixtures/dummy.pdf` proves the offline workflow; `.milvus/` (git-ignored) stores Milvus Lite state; `.cache/docling_milvus_rag/` hosts embedding + Docling caches.
- **Tests**: `tests/` contains backend + CLI verification (`test_rag_pipeline.py`, upcoming CLI integration tests). UV dev extras expose `pytest` so `uv run pytest` just works.

## 3. Pyproject & UV Metadata Plan
| Concern | Configuration |
| --- | --- |
| Project metadata | `[project]` stays as defined (name, version, authors, Python >=3.11). Description highlights offline Docling→Milvus goal. |
| Dependency groups | Runtime deps already listed (Docling, PyMilvus, SentenceTransformers, LangChain splitters, structlog, Pydantic, numpy, llama-cpp, pypdf, Typer, Rich). Dev/test deps live both in `[project.optional-dependencies.dev]` and `[tool.uv.dev-dependencies]` to keep `uv` + hatch aligned. |
| CLI entry point | Add `[project.scripts]` with `docling-milvus-rag = "docling_milvus_rag.cli:app"` (Typer automatically exposes the command). Provide `__main__.py` that calls `from docling_milvus_rag.cli import app; app()` for `python -m docling_milvus_rag` parity. |
| UV command shortcuts | Document official invocations instead of inventing ad-hoc scripts: `uv run docling-milvus-rag ...` for CLI, `uv run python -m docling_milvus_rag.cli --help` for debugging, `uv run pytest -k rag_pipeline` for targeted tests. |
| Environment defaults | `tool.uv` keeps dev deps; no extra `uv` sections needed yet, but we’ll add `tool.uv.sources = ["src"]` only if multi-root editing ever appears. |

## 4. Dependency & Versioning Constraints
1. **Runtime set** (pyproject lines 12–25) already capture minimal libs; keep them upper-bounded by semantic major when upstream instability is known (e.g., `docling>=2.2.0,<3.0` once validated). Typer/Rich pinned to minor to avoid CLI regressions.
2. **Offline guarantees**: `sentence-transformers` + `llama-cpp-python` require cached weights; document prefetch instructions in README and optionally vendor small GGUF/embedding checkpoints under `models/` for air-gapped installs.
3. **Extra hooks**: Provide optional extras for GPU acceleration later (`[project.optional-dependencies.gpu]` bundling CUDA-enabled wheels) but keep base install CPU-only for portability.
4. **Validation**: Run `uv pip check` (built into `uv run pip check`) inside CI after lockfile updates to ensure dependency resolution stays healthy.

## 5. Lockfile & Reproducibility Strategy
- Treat `uv.lock` as mandatory artifact; regenerate with `uv lock --locked --python 3.11` whenever dependencies change, committing diffs alongside `pyproject.toml`.
- CI should execute `uv sync --frozen` to fail fast if lockfile/pyproject drift.
- Document `uv export --format requirements.txt --locked` as the fallback for environments that still expect pip requirements.
- Store `UV_CACHE_DIR=.cache/uv` inside repo (git-ignored) so repeated `uv run` commands hit >90% cache hit rate locally without polluting global caches.

## 6. Command Wiring & Script Flow
1. **Setup**
   - `uv sync --all-extras` (during development) installs runtime + `dev` extras.
   - `uv run preflight` (Typer command exposed later) can report environment readiness (Python version, Milvus path, cache directories) before executing pipeline.
2. **Execution**
   - `uv run docling-milvus-rag --pdf fixtures/dummy.pdf --question "Summarize" ...` hits the Typer entry point, which converts CLI args into the `ConfigBuilder` contract and calls `Pipeline.run()`.
   - A `--dry-run` flag short-circuits after validation/logging, satisfying FR8.
3. **Testing**
   - `uv run pytest tests/test_rag_pipeline.py -q` ensures backend determinism.
   - Future CLI tests call `uv run pytest tests/test_cli_entrypoint.py -q` and internally shell out with `uv run docling-milvus-rag ...` to stay faithful to published UX.
4. **Maintenance**
   - Provide `uv run docs` (Typer command or Python module) later if docs generation becomes necessary; for now, README instructions suffice.

## 7. Configuration Layering & Flag Mapping
| Layer | Mechanism | Notes |
| --- | --- | --- |
| Defaults | `config/defaults.toml` read at startup | Mirrors CLI defaults: dummy PDF, `chunks` export, local Milvus Lite URI, baseline chunk sizes, embedding/LLM configs. |
| Environment | `DOCMILVUS_*` env vars mapped via `pydantic-settings` | Enables CI or users to predefine `DOCMILVUS_MILVUS_URI`/`DOCMILVUS_LOG_LEVEL` without flags. |
| CLI | Typer arguments | Flags from requirements (`--pdf`, `--export-type`, `--milvus-uri`, `--collection`, `--question`, `--top-k`, `--chunk-size`, `--chunk-overlap`, `--embedding-model`, `--llm-backend`, `--log-level`, `--output`, `--dry-run`) override everything else. |

## 8. Build/Cache Performance Targets
- **Cold start**: `uv sync` under 30s using cached wheels; maintain wheelhouse via `uv cache prune --days 30` in CI to avoid bloat.
- **Hot runs**: `uv run docling-milvus-rag` uses existing `.venv` from UV; Typer command should load in <5s post-cache thanks to `sentence-transformers` lazy model instantiation.
- **Milvus Lite**: store path default `.cache/milvus_lite/docling.db`; CLI auto-creates directories to prevent repeated init penalties.
- **Embedding cache**: pipeline-level caching ensures re-ingestion/insertion is skipped when checksums match (documented for CLI users via `--wipe-store/--persist-store`).

## 9. Observability & Developer Experience
- Standardize logging via `structlog` with consistent markers (`PIPELINE_START`, `MILVUS_INSERT`, `PIPELINE_COMPLETE`).
- Provide `--log-level` + `--json-logs` flags; CLI toggles `structlog` processors accordingly.
- Document `uv run docling-milvus-rag --help` output (<80 lines) with grouped sections (Documents, Retrieval, Vector Store, Output, Diagnostics) to satisfy NFR1–NFR3.

## 10. Acceptance Criteria Traceability
- `uv` commands + scripts guarantee FR1 (single entry) and FR7/NFR5 (config layering + scriptability) because they enforce deterministic invocation + exit codes (0 success, 2 validation, 3 runtime errors).
- Prefetch + caching recommendations uphold offline assumption (no HuggingFace tokens, local Milvus) per FR2–FR6.
- Lockfile discipline (`uv lock` + `uv sync --frozen`) ensures reproducibility for QA/CI, aligning with stakeholder need for deterministic smoke tests.

This architecture gives the upcoming CLI developer a precise contract for wiring Typer arguments into the backend while ensuring UV delivers fast, reliable, and reproducible executions.
