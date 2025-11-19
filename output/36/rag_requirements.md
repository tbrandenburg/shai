# Docling–Milvus RAG Requirements

## Context Summary
- Source issue (output/36/issue_conversation.md) requests a "very simple" local project that repackages the Docling RAG Colab (`docs/examples/rag_langchain.ipynb`) into a UV-managed CLI runnable via `uv run docling-milvus-rag`.
- The Colab demonstrates a Docling loader feeding LangChain, HuggingFace sentence-transformer embeddings, Milvus vector storage, and a remote HuggingFace Inference API LLM using a Docling technical report PDF.
- New solution must execute fully offline (no HuggingFace token dependency) yet still showcase Docling ingestion, chunking, embedding, Milvus storage, and answer generation on a dummy local PDF.

## Stakeholders & Goals
- **Project sponsor (@tbrandenburg):** Validate Docling→Milvus RAG workflow locally without Colab or hosted services; simplify onboarding via UV.
- **Developers / ML engineers:** Need deterministic environment, modular codebase, and replaceable components for future iterations.
- **QA / Operators:** Require predictable CLI contract plus fixture PDF to prove the pipeline end-to-end.

## Constraints & Assumptions
- Must avoid HuggingFace API tokens entirely; embeddings/LLM must run with locally available weights or other non-token-gated providers.
- Execution command is `uv run docling-milvus-rag` from repo root using UV-managed virtual environment (`pyproject.toml` + `uv.lock`).
- Pipeline ingests at least one bundled dummy PDF (e.g., `fixtures/dummy.pdf`) rather than downloading external files.
- Milvus usage should rely on the lightweight local Milvus client (`connection_args={"uri": <path>}`) rather than requiring a remote server.
- Keep project minimal: single CLI entry point, limited dependencies, clear configuration defaults, and no unnecessary orchestration layers.

## Prioritized Functional Requirements (with Acceptance Criteria)
1. **FR1 – Local Docling ingestion and chunking (Priority: Must)**
   - Pipeline loads local PDFs via `DoclingLoader` with support for both `ExportType.DOC_CHUNKS` and `ExportType.MARKDOWN` (default chunks).
   - Acceptance Criteria:
     - Running `uv run docling-milvus-rag --pdf fixtures/dummy.pdf` logs Docling ingestion start/completion.
     - Resulting document chunks (or markdown docs) expose metadata compatible with downstream LangChain components.

2. **FR2 – Offline embeddings and LLM answering (Priority: Must)**
   - Replace HuggingFace Inference API with locally runnable/open-weight models (e.g., sentence-transformers via `HuggingFaceEmbeddings` cached locally plus an LLM served through `llama-cpp`, `ctransformers`, or other non-token backend).
   - Acceptance Criteria:
     - Command executes without `HF_TOKEN` set and without network calls to HuggingFace endpoints.
     - Sample run produces an answer string sourced from retrieved chunks (even if heuristic/dummy) proving retrieval + generation loop works offline.

3. **FR3 – Milvus vector store persistence (Priority: Must)**
   - Use LangChain Milvus client configured with a filesystem URI (sqlite-backed) or embedded deployment, auto-initialized per run unless overridden.
   - Acceptance Criteria:
     - CLI argument/environment allows specifying Milvus URI, defaulting to a temp path within the project.
     - After execution, vector store contains embeddings for each chunk (verifiable via retrieval count or logging statement).

4. **FR4 – Configurable question answering workflow (Priority: Should)**
   - Provide CLI flags/env vars for question prompt, top-k retrieval, embedding model, and export type (fallback to sensible defaults mirroring the Colab).
   - Acceptance Criteria:
     - `uv run docling-milvus-rag --question "..." --top-k 5` overrides defaults and reflected in logs/results.

5. **FR5 – Dummy PDF fixture & verification (Priority: Must)**
   - Include a small dummy PDF under `fixtures/` and ensure pipeline references it in README/examples/tests.
   - Acceptance Criteria:
     - Running pipeline with no args ingests bundled dummy PDF and outputs reproducible answer.
     - Tests/readme document fixture location and usage.

6. **FR6 – Deterministic UV project structure (Priority: Must)**
   - Provide `pyproject.toml` + `uv.lock`, `src/docling_milvus_rag/` package, CLI entry point, and README usage instructions.
   - Acceptance Criteria:
     - `uv run docling-milvus-rag` (after `uv sync`) completes without additional manual setup.
     - Project layout reflects modular pipeline components (loader, embedder, vector store, QA loop).

7. **FR7 – Logging and observability (Priority: Could)**
   - Emit structured logs for ingestion count, vector inserts, retrieval hits, and final answer snippet for troubleshooting.
   - Acceptance Criteria:
     - CLI output includes timestamps/levels and at least one log entry per pipeline phase.

## Non-Functional Requirements
- **NFR1 – Reproducibility:** UV lockfile pins versions; README documents Python version and UV usage instructions.
- **NFR2 – Simplicity:** Keep dependencies close to the Colab example but trimmed to essentials (Docling, LangChain components, Milvus client, local LLM backend).
- **NFR3 – Offline readiness:** No external downloads during runtime beyond initial pip/uv sync; dummy assets stored locally.
- **NFR4 – Testability:** Provide automated tests covering pipeline ingestion + retrieval to support CI usage.
- **NFR5 – Documentation:** README must summarize architecture, commands, and fixture usage in <2 minutes reading time.

## Acceptance Validation Plan
1. Install via `uv sync`, then run `uv run docling-milvus-rag --pdf fixtures/dummy.pdf --question "<sample>"` to verify ingestion, embedding, Milvus insert, and answer output without tokens.
2. Execute automated tests to confirm vector store population and CLI exit codes.
3. Inspect logs and output artifacts ensuring offline execution and dummy PDF coverage.
