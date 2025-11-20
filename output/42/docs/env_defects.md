# Feature 3 – Config Defect Triage (error-detective)

## Root Causes
1. **Lint regression (B008, UP035)** – `pyrag/cli.py` instantiated Typer options in default arguments and `pyrag/config.py` imported `Mapping` from `typing`, triggering Ruff failures noted in `env_test_results.md`.
2. **Editable build failure** – setuptools discovered both `pyrag` and the archived `tmp_cli_debug2` payload as top-level packages, so every `uv run --extra dev pytest`/`uv run pyrag` attempt exited before tests (see `env_build_log.md`).
3. **CLI parsing regressions** – Typer 0.12.5 is incompatible with Click 8.3.x (TypeError when rendering help) and, with only a single registered command, collapses the CLI into a root command, so `CliRunner` (and `pyrag run …`) reported "unexpected extra argument (run)" once packaging succeeded.

## Remediations
- Reworked `pyrag/cli.py` to:
  - Keep the Typer command definitions but add a lightweight `@app.callback()` so Typer exposes `run` as an actual subcommand for groups.
  - Centralize CLI overrides via `_build_overrides`, call `configure()` + `emit_settings_snapshot()`, and retain the Typer option defaults with explicit `# noqa: B008` markers (satisfies Ruff while preserving Typer semantics).
- Imported `Mapping` from `collections.abc` inside `pyrag/config.py` to comply with UP035.
- Pinned packaging scope to the intended module with `[tool.setuptools]
packages = ["pyrag"]` inside `pyproject.toml`, preventing setuptools from inspecting `tmp_cli_debug2`.
- Added an explicit runtime dependency on `click>=8.1,<8.2` so Typer 0.12.5 installs a compatible Click release.

## Verification
- `uv tool run --project /home/runner/work/shai/shai/output/42 ruff check`
- `uv run --project /home/runner/work/shai/shai/output/42 --extra dev pytest`
- `uv run --project /home/runner/work/shai/shai/output/42 pyrag run --env-file /home/runner/work/shai/shai/output/42/.env.example`
- `DOC_CACHE_DIR=/home/runner/work/shai/shai/output/42/.pyrag_cache_alt TOP_K=4 CHUNK_SIZE=600 CHUNK_OVERLAP=100 LOG_LEVEL=DEBUG VALIDATION_ENABLED=true METRICS_VERBOSE=true uv run --project /home/runner/work/shai/shai/output/42 pyrag run`

All four commands now exit with code 0, demonstrating lint/packaging parity plus both CLI scenarios functioning end-to-end.

## Prevention / Follow-ups
- Keep the Click dependency pinned until Typer officially supports Click ≥8.3.
- Retain the dummy Typer callback (or add additional subcommands) whenever future work expands the CLI, ensuring the public contract (`pyrag run …`) stays stable.
- When archiving intermediate artifacts (e.g., `tmp_cli_debug2`), place them outside of the package root or update setuptools configuration immediately to avoid rediscovery in editable builds.
