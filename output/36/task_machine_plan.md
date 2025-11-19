## Context
The team must turn the Docling RAG Colab example into a minimal UV-managed Python project that can be executed locally with `uv run docling-milvus-rag`, avoids any HuggingFace token requirements, and proves the workflow with a dummy PDF input end to end.

## Role Descriptions
### business-analyst
- Agent Path: `.github/agents/08-business-product/business-analyst.md`

### llm-architect
- Agent Path: `.github/agents/05-data-ai/llm-architect.md`

### backend-developer
- Agent Path: `.github/agents/01-core-development/backend-developer.md`

### build-engineer
- Agent Path: `.github/agents/06-developer-experience/build-engineer.md`

### cli-developer
- Agent Path: `.github/agents/06-developer-experience/cli-developer.md`

### test-automator
- Agent Path: `.github/agents/04-quality-security/test-automator.md`

## Chronologic Task List
**Feature 1 – Docling RAG pipeline adaptation**
- [x] [business-analyst] Requirement synthesis — Review `output/36/issue_conversation.md` alongside the referenced Colab notebook to capture explicit functional/non-functional needs (Docling ingestion, Milvus usage, dummy PDF test, no HuggingFace token) and save a prioritized list with acceptance criteria to `output/36/rag_requirements.md`.
  * Summary: Consolidated Docling→Milvus requirements into prioritized FR/NFR list with offline/UV constraints and acceptance criteria in `output/36/rag_requirements.md`.
- [x] [llm-architect] System architecture — Read `output/36/rag_requirements.md`, inspect the Colab notebook code path, and design a modular Docling→chunking→embedding→Milvus→LLM answering flow covering component contracts, dependency choices, and configuration defaults; record diagrams and dataflow notes in `output/36/rag_architecture.md`.
  * Summary: Captured Docling→Milvus offline architecture with component contracts, dependency/LLM choices, config defaults, and flow diagrams in `output/36/rag_architecture.md`.
- [x] [backend-developer] Module design — Using `output/36/rag_architecture.md`, define Python package layout (e.g., `src/docling_milvus_rag/pipeline.py`, `config.py`, `milvus_store.py`), configuration loading strategy, and interfaces for ingesting local PDFs without remote credentials; document this detailed plan in `output/36/rag_module_design.md`.
  * Summary: Captured package layout, config layering, and offline ingestion interfaces in `output/36/rag_module_design.md`.
- [x] [backend-developer] Pipeline implementation — Follow `output/36/rag_module_design.md` to build the Docling RAG modules under `src/docling_milvus_rag/`, wire Milvus client initialization that works offline, ensure embeddings/models rely on locally accessible providers, add a sample dummy PDF under `fixtures/dummy.pdf`, and update `pyproject.toml` plus `uv.lock` so dependencies resolve via `uv run`.
  * Summary: Added the full offline-friendly package under `src/docling_milvus_rag/`, wired caching + Milvus Lite fallback, created defaults/dummy PDF fixtures, and introduced `pyproject.toml` with a pinned `uv.lock` for `uv run docling-milvus-rag`.
- [x] [test-automator] Pipeline verification — Create `tests/test_rag_pipeline.py` that loads `fixtures/dummy.pdf`, runs the pipeline entrypoint, and asserts vector store population plus answer generation; capture execution logs, sample outputs, and pass/fail status in `output/36/rag_test_report.md`.
  * Summary: Added pytest-based pipeline coverage, captured sample run evidence, and logged the passing results in `output/36/rag_test_report.md`.

**Feature 2 – UV CLI packaging & execution experience**
- [x] [business-analyst] CLI requirement brief — Analyze `output/36/rag_requirements.md` plus any stakeholder notes to describe expected CLI ergonomics (flags for Milvus URI, paths for documents, output formatting) and document them with usage scenarios inside `output/36/cli_requirements.md`.
  * Summary: Captured offline-first CLI flags, configuration layering, and usage scenarios with acceptance criteria in `output/36/cli_requirements.md`.
- [x] [build-engineer] UV project architecture — Read `output/36/cli_requirements.md` to define the UV workspace layout, dependency constraints, and reproducible lockfile strategy; specify scripts, `pyproject.toml` metadata, and `uv run` command wiring inside `output/36/uv_build_architecture.md`.
  * Summary: Documented UV workspace layout, dependency/lock strategy, and command wiring in `output/36/uv_build_architecture.md` so `uv run docling-milvus-rag` stays deterministic and offline-friendly.
- [x] [cli-developer] Command design — Based on `output/36/uv_build_architecture.md`, describe the CLI command tree for `docling-milvus-rag`, list arguments/env vars, outline help text, and determine how results/dummy PDF checks surface; store this plan in `output/36/cli_command_design.md`.
  * Summary: Captured Typer command tree, flag/env matrix, help text grouping, and dummy PDF validation workflow inside `output/36/cli_command_design.md`.
- [x] [cli-developer] CLI implementation — Implement the command described in `output/36/cli_command_design.md` by adding `src/docling_milvus_rag/cli.py` (and `__main__.py` if needed), exposing an entry point in `pyproject.toml`, wiring logging plus error handling, and updating README usage notes so `uv run docling-milvus-rag --pdf fixtures/dummy.pdf` executes the pipeline.
  * Summary: Delivered Typer-based CLI with default `run` behavior, preflight/store utilities, README usage docs, and a `[project.scripts]` entry so `uv run docling-milvus-rag --pdf fixtures/dummy.pdf` runs the offline pipeline end to end.
- [x] [test-automator] CLI integration tests — Author `tests/test_cli_entrypoint.py` that shells out via `uv run docling-milvus-rag --pdf fixtures/dummy.pdf`, captures stdout/stderr, and validates exit codes plus output artifacts; summarize coverage gaps and test evidence in `output/36/cli_test_report.md`.
  * Summary: Added pytest that shells out to `uv run docling-milvus-rag` with isolated artifacts, skips gracefully when `uv` is absent, and documented the current skipped state plus rerun guidance inside `output/36/cli_test_report.md`.
