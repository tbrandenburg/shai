# UV Packaging Requirements

## Objective
Embed the existing Docling-based LangChain RAG script inside a UV-managed project so stakeholders can run the entire workflow with a single `uv run pyrag` command while preserving the simple loader → chunker → embedder → storage → search structure.

## Scope of Work
- Package the script into a UV project with a clearly named CLI (`pyrag`).
- Restructure the codebase into discrete modules (loader, chunker, embedder, storage, search) without adding net-new functionality beyond structural clarity.
- Adopt `sentence-transformers/all-MiniLM-L6-v2` for embeddings and ensure no HuggingFace token is required for inference.
- Keep Docling + LangChain RAG flow deterministic and transparent for downstream contributors.

## CLI Expectations
- Only supported invocation: `uv run pyrag`; no additional CLI arguments or environment variables required to execute the default pipeline.
- CLI must load configuration (e.g., `.env`) automatically and print the same informational steps now produced by the script (loading, splitting, indexing, querying, responses, retrieved sources).
- Provide helpful warnings if optional environment values (e.g., `HF_TOKEN`) are absent, but do not fail the run.
- Exit with non-zero status only when the pipeline encounters blocking errors (missing dependencies, invalid configuration, runtime failures).

## Dependency Requirements
- Manage dependencies exclusively through UV (`pyproject.toml` + `uv.lock`).
- Core libraries: `langchain`, `langchain-core`, `langchain-docling`, `langchain-milvus`, `langchain-huggingface`, `langchain-text-splitters`, `docling`, `sentence-transformers`, `python-dotenv`, `pymilvus` (if not bundled), and any transitive requirements for Docling + Milvus integration.
- Ensure `sentence-transformers/all-MiniLM-L6-v2` downloads without authentication; avoid configuring HuggingFace Hub tokens for embeddings.
- Include developer tooling dependencies for formatting (`ruff`) and testing (built-in or pytest as needed for validation flow).
- Document OS-level prerequisites (Milvus client library, C++ build tools if required) inside README/requirements notes.

## Linting & Testing Obligations
- Repository must pass `uv ruff format` and `uv ruff check` with no warnings.
- Provide at least a smoke test or validation script demonstrating the modular pipeline still runs end-to-end via `uv run pyrag` after packaging.
- Any future CI should run the above commands plus `uv run pyrag` to validate packaging integrity.

## Configuration & Environment
- Include `.env.example` enumerating optional values (e.g., `HF_TOKEN`) but emphasize that no token is required for default execution.
- Default configuration should embed the current demo parameters: Docling Technical Report URL, export type, embedding/retrieval settings, and query prompt.
- Temporary storage (e.g., Milvus local URI) must be created within the CLI run, preferably via `tempfile` utilities, so no manual setup is needed.

## Acceptance Criteria
1. UV project installs and locks dependencies; `uv run pyrag` executes end-to-end without extra arguments.
2. Codebase organized into loader/chunker/embedder/storage/search modules that map cleanly onto the existing pipeline logic.
3. Embeddings rely on `sentence-transformers/all-MiniLM-L6-v2` without requiring a HuggingFace token.
4. Formatting (`uv ruff format`) and linting (`uv ruff check`) both succeed.
5. Documentation (README and/or CLI help) explains how to run the project, prerequisites, and expected outputs.
6. Validation evidence (logs or summary) stored in repo proving the packaged pipeline produces results comparable to the original script.

## Risks & Mitigations
- **Model download latency**: Cache the embedding model locally via UV’s virtualenv to avoid repeated downloads; document the first-run cost.
- **Milvus dependency complexity**: Use local `Milvus` Lite or file-based store configuration to prevent external service requirements.
- **Environment drift**: Lock versions with UV and record exact commands used to (re)generate locks.

## Traceability
All requirements trace back to Issue #42 directives and the Context section of `task_machine_plan.md`. Downstream architecture, design, and implementation artifacts must reference this document to maintain alignment.
