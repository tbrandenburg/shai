# pyrag

Offline-first CLI that ingests a PDF, builds a lightweight vector index, and answers a question without any hosted APIs. All code lives in the `pyrag` package so the entrypoint can be executed with `uv run pyrag`.

## Quickstart
1. Install uv (https://github.com/astral-sh/uv) if it is not already available.
2. From this directory run `uv sync` to create the virtual environment and install dependencies declared in `pyproject.toml` / `uv.lock`.
3. Execute the CLI:
   ```bash
   uv run pyrag --pdf tests/fixtures/dummy.pdf --query "What does the document cover?"
   ```

- Default PDF path is `tests/fixtures/dummy.pdf`; override it with `--pdf`.
- The CLI only needs Typer + PyPDF at runtime. Sentence Transformers is optional and only used when installed.
- All caches are stored under `.uv-cache/pyrag/` so repeated runs avoid re-downloading assets.
