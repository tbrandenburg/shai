# Feature 3 – Config Testing (test-automator)

All commands executed from `output/42` to validate the reduced nine-variable configuration surface. Results reference `output/42/env_build_log.md` for prior implementation notes.

## Command Timeline

| Command | Timestamp (UTC) | Exit Code | Notes |
| --- | --- | --- | --- |
| `uv tool run ruff format` | 2025-11-19T22:05:00Z | 0 | Formatter touched 15 files but no changes were needed; confirms tree is already formatted per Ruff expectations. |
| `uv tool run ruff check` | 2025-11-19T22:06:00Z | 1 | Fails with B008 (Typer option defined in default argument for `run_command`) and UP035 (import `Mapping` from `collections.abc` in `pyrag/config.py`). These regressions block the test gate until addressed. |
| `uv run --extra dev pytest` | 2025-11-19T22:07:00Z | 1 | Build phase aborts before tests because setuptools detects multiple top-level packages (`pyrag`, `tmp_cli_debug2`). Matches the issue captured in `env_build_log.md`; no test modules executed. |
| `uv run pyrag run --env-file .env.example` | 2025-11-19T22:09:00Z | 1 | Same editable build failure caused by `tmp_cli_debug2` being treated as an extra package, so the CLI never starts; behavior again mirrors `env_build_log.md`. |
| `DOC_CACHE_DIR=.pyrag_cache_alt TOP_K=4 CHUNK_SIZE=600 CHUNK_OVERLAP=100 LOG_LEVEL=DEBUG VALIDATION_ENABLED=true METRICS_VERBOSE=true uv run pyrag run` | 2025-11-19T22:11:00Z | 1 | Overriding env vars via shell reproduces the identical packaging failure before runtime; unable to observe logging, chunk sizing, or validation toggles. |

## Observations

- Lint compliance is currently broken by a Typer option instantiation pattern and a typing import location; fixing both is required before CI can pass.
- Every executable that depends on building the editable wheel (`pytest`, `uv run pyrag`) fails because the repo root still contains `tmp_cli_debug2`, causing setuptools to refuse discovery. This is the same blocker noted in `env_build_log.md`, so defect triage can reference that log for traceability.
- Because the build step fails early, no runtime validation of log-level switching, chunk sizing, or Milvus configuration is yet possible; once packaging is fixed, rerun the two CLI scenarios above to collect behavioral evidence.
