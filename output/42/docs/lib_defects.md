# Feature 4 - Defect Log (2025-11-20)

## Detection Summary
- Triaged the failures recorded in `lib_test_results.md` by rerunning `uv tool run ruff check output/42` and `cd output/42 && uv run --locked --no-sync pytest tests` (7 passed in 93s) once each fix landed to confirm lint/test health.

## Findings

### DEF-001 - Ruff UP035/UP037 regressions
- **Symptom:** `uv tool run ruff check` flagged UP035 in `pyrag/chunker.py` and `pyrag/embedder.py` plus UP037 in `pyrag/storage.py`, blocking the lint gate.
- **Root cause:** The Feature 3 typing style (importing `Iterable` from `typing` and quoting forward references) was left in place after moving to Python 3.12 + Ruff modernization.
- **Fix:** Updated both modules to import `Iterable` from `collections.abc` and removed the obsolete quoted `_LiteRetriever` return type in `pyrag/storage.py` so Ruff no longer reports modernization issues.
- **Prevention:** Keep Ruff enabled locally when touching shared modules; the UP03x rules catch these regressions immediately.

### DEF-002 - Docling fallback cache missing
- **Symptom:** `tests/test_modules.py::test_loader_materializes_cache_and_chunks` observed that `docling_source.json` never appeared when the loader fell back, causing the test (and downstream stages) to fail fast.
- **Root cause:** `_fallback_payload()` never wrote the serialized payload to `PipelineSettings.docling_source_path`, so cache-dependent tests saw an empty directory and repeated fallback work.
- **Fix:** When `_materialize_payload()` raises, `DoclingLoader.load()` now persists the fallback payload/metadata and tags the metrics with `cache_hit=False`, restoring the deterministic cache contract.
- **Prevention:** Loader unit test now enforces cache creation, so any regression re-triggers the failure before release.

### DEF-003 - MiniLM hash forcing ignored
- **Symptom:** `_force_hash_embeddings()` could not disable the heavy HuggingFace model, so module and pipeline tests received real 384-dimensional vectors and failed assertions that expect the 8-value deterministic hash.
- **Root cause:** The implementation dropped the historical `_ensure_model` hook while `tests/test_modules.py` still monkeypatches that method, making the patch a no-op.
- **Fix:** Reintroduced `_ensure_model()` (wrapping the actual HuggingFace client factory) and had `_vectorize()` call it, which lets the tests stub the model loader and forces the hash fallback deterministically.
- **Prevention:** Leave thin compatibility shims like `_ensure_model()` in place when refactoring shared modules so contract-driven tests keep control over external dependencies.

### DEF-004 - Offline validation assumptions in tests
- **Symptom:** `test_pipeline_runner_emits_summary` assumed a single fallback document/metric count, and the Typer CLI smoke test expected validation to pass even when HuggingFaceEndpoint is unreachable, yielding pytest failures and exit code mismatches.
- **Root cause:** After enabling the real Docling + LangChain stack, the loader now yields dozens of chunks when Docling succeeds and validation enforces non-fallback LLMs, but the tests still asserted the old stub behavior.
- **Fix:** Relaxed the pipeline assertions to `>= 1` for document/metric counts and invoked the CLI with `--validation-enabled false` so the smoke run exercises the full CLI while explicitly opting into the documented offline override.
- **Prevention:** Documented the offline toggle in the CLI test and future defect logs so QA remembers to disable validation when the hosted HuggingFace endpoint is unavailable.
