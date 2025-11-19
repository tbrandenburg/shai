# Feature 1 – CLI Notes (cli-developer)

## uv + Entry Point Wiring
- `pyproject.toml` defines `pyrag` as the project name with `[project.scripts] pyrag = "pyrag.__main__:cli"`, allowing `uv run pyrag` to call the package entry point without manual Python invocations.
- `.venv` is fully managed by `uv lock` / `uv run`, so the only runtime dependency that gets installed is `pypdf` (the rest of the stack is stdlib code in `pyrag/`).
- The CLI defaults to the argparse implementation to dodge recent Typer/Rich rendering bugs in minimal uv environments, but the Typer code path is still present if a future release re-enables it safely.

## Typical Usage
```bash
uv run pyrag --pdf tests/fixtures/dummy.pdf --query "What is the document about?"
```
- `--pdf` defaults to `tests/fixtures/dummy.pdf`, so once the fixture lands you can omit it when validating.
- `--query` is required; wrap multi-word prompts in quotes.
- Adjust chunking (`--chunk-size`, `--chunk-overlap`), retrieval depth (`--k`), and backends (`--retriever-backend`, `--llm-backend`) through the documented flags.
- `--verbose` increases logging and `--log-file path/to/log.txt` mirrors the console output for QA ingestion.
- All caches live under `.uv-cache/pyrag/` as described in `pyrag/config.py`, so repeated runs are deterministic and local-only.

## Troubleshooting
- **Missing dummy PDF**: the default `tests/fixtures/dummy.pdf` must exist before running. Override with `--pdf` or create the fixture (next task).
- **Path issues on uv run**: ensure you execute `uv run pyrag` from `output/41/`; uv needs the local `pyproject.toml` to resolve dependencies and the entry point.
- **Typer-specific flags**: until Typer stabilizes its Rich help output inside uv sandboxes, the CLI deliberately falls back to argparse even if Typer is installed. Re-enable the Typer branch only after validating a compatible Typer + Rich combination locally.
- **Dependency drift**: rerun `uv lock` after any `pyproject.toml` tweak so the lockfile stays in sync with the single `pypdf` dependency and the slim CLI footprint is preserved.
