# Feature 4 – Validation Run (test-automator)

All validation commands were issued from `output/42` and build context references `output/42/lib_build_log.md` for the reinstated LangChain/Docling pipeline details.

## Command Timeline

| Command | Timestamp (UTC) | Exit Code | Notes |
| --- | --- | --- | --- |
| `uv tool run ruff format` | 2025-11-20T07:34:30Z | 0 | Formatter downloaded Ruff into the uv tool cache and reported "15 files left unchanged", so formatting already matched repo policy. |
| `uv tool run ruff check` | 2025-11-20T07:34:50Z | 1 | Ruff surfaced UP035 violations in `pyrag/chunker.py` and `pyrag/embedder.py` (import `Iterable` from `collections.abc`) plus UP037 in `pyrag/storage.py` (quoted type alias); these block the lint gate until refactors follow the `lib_design.md` guidance. |
| `uv run --extra dev pytest /home/runner/work/shai/shai/output/42/tests` | 2025-11-20T07:36:30Z | 1 | Test session failed 4 cases: loader stub never wrote `docling_source.json`; MiniLM embeddings returned real 384-dim vectors instead of the deterministic 8-value hash expected by `_force_hash_embeddings`; the Typer CLI exited 1 because validation stayed strict and ONNX runtime is unavailable; pipeline summary expected 1 doc but real Docling load yielded 49 chunks plus an `_ARRAY_API` error from `onnxruntime`. |
| `set -a && . ./.env.example && set +a && uv run pyrag run` | 2025-11-20T07:37:01Z | 1 | Baseline CLI run exercised the loader→search flow but ended with `Validation failed: LLM fallback triggered; rerun with a reachable HuggingFaceEndpoint`, proving the default `VALIDATION_ENABLED=true` path still requires a hosted endpoint that is unavailable in the task-machine sandbox. |
| `DOC_CACHE_DIR=.pyrag_cache_alt TOP_K=3 CHUNK_SIZE=800 CHUNK_OVERLAP=120 VALIDATION_ENABLED=false METRICS_VERBOSE=true uv run pyrag run --top-k 3 --chunk-size 800 --chunk-overlap 120 --metrics-verbose true --validation-enabled false` | 2025-11-20T07:37:19Z | 0 | Inline overrides redirected cache writes to `.pyrag_cache_alt`, downshifted validation, and emitted the metrics table; retrieval succeeded with deterministic stub chunks and `Validation passed for retrieval depth 3`, confirming env toggles propagate through `PipelineSettings`. |

## Observations

- Linting is currently blocked by two `typing` imports and one quoted type alias; `error-detective` should adjust those modules so Ruff UP035/UP037 pass before CI resumes.
- Runtime tests reveal that loader, embedder, CLI, and pipeline fixtures still assume the deterministic stubs documented in `lib_design.md`; either the fixtures must pin to the stub helpers (e.g., ensure `_force_hash_embeddings` is respected) or the implementation needs additional gating so doc cache artifacts are written and chunk counts shrink to the expected single document.
- Docling continues to attempt ONNX-backed OCR which fails because `_ARRAY_API` is unavailable; `lib_build_log.md` already noted fallback paths, so defect triage can either install an ONNX-compatible build or mock the loader responses in tests/CLI validation to avoid the heavy OCR path.
- Validation of `uv run pyrag run` proved that `.env` defaults enforce strict validation (failing without HuggingFaceEndpoint) whereas overriding `VALIDATION_ENABLED=false` allows the rest of the stack to run; document this behavior for operators so they know the CLI currently requires offline overrides.
