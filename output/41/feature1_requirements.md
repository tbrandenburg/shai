# Feature 1 – Requirements Capture

## Source Inputs
- Issue brief (`output/41/issue_conversation.md` / `issue_context.json`)
- Task Machine context (LangChain Docling RAG notebook migration)
- Repository expectation: uv-managed CLI invoked as `uv run pyrag`

## User Stories
| ID | Story | Source | Notes |
| --- | --- | --- | --- |
| US1 | As a stakeholder, I need a single Python entrypoint that mirrors the LangChain Docling RAG notebook so I can run the knowledge retrieval workflow locally without Colab. | Original issue | Eliminates notebook dependencies; code should be production-friendly. |
| US2 | As an operator, I want to invoke the pipeline via `uv run pyrag --pdf <path> --query <text>` so setup is just `uv` install plus one command. | Original issue | Requires wiring CLI script + uv project metadata. |
| US3 | As QA/analyst, I must validate the workflow using a dummy PDF to ensure predictable deterministic smoke tests. | Original issue | Dummy file should reside in repo (e.g., `tests/fixtures/dummy.pdf`). |
| US4 | As a compliance/security stakeholder, I need the system to run without any Hugging Face token so it can execute in locked-down environments. | Original issue | Requires choosing embedding/model providers that do not require auth or using local/offline embedding models. |
| US5 | As a maintainer, I want minimal, transparent dependencies and clear configuration so onboarding is fast and uv lockfiles are stable. | Context | Keep dependency footprint lean; document configuration defaults. |

## Constraints & Non-Negotiables
- **No Hugging Face tokens**: All models/embeddings must execute without authentication; prefer open-source/local embeddings (e.g., `SentenceTransformers` local models) or other providers bundled with LangChain/Docling.
- **Single-file entrypoint**: The notebook’s logic must collapse into a primary Python CLI module (later design may split helpers, but entrypoint is one executable script exposed as `pyrag`).
- **uv-managed project**: Dependencies resolved via `uv`; `pyproject.toml` + `uv.lock` define runtime; no pip/conda instructions.
- **CLI contract**: Command `uv run pyrag --pdf <file> --query <question>` (with sensible defaults) must drive the entire RAG workflow end-to-end.
- **Dummy PDF validation**: Repo must include or reference a sample PDF to prove ingestion/pipeline correctness during tests.
- **Lightweight dependencies**: Only bring in libraries strictly required for Docling PDF parsing, chunking, embeddings, vector store, and QA; document any heavyweight assets.
- **Offline-first**: Pipeline should not assume internet access beyond fetching initial dependencies (runs offline after install).
- **Traceability**: Each requirement should map to implementation/test artifacts for downstream roles (design, coding, QA).

## Acceptance Criteria
- **AC1 (US1)**: Repo contains Python sources replicating the Colab workflow, with docstrings/comments noting any deviations; running `uv run pyrag --pdf tests/fixtures/dummy.pdf --query "What is inside?"` succeeds without manual notebook steps.
- **AC2 (US2)**: `pyproject.toml` exposes console script/entrypoint `pyrag`; `uv run pyrag -h` displays CLI options for PDF path, query text, chunk sizing, and output verbosity.
- **AC3 (US3)**: Dummy PDF fixture is documented plus referenced in README/CLI help; automated validation uses it to prove pipeline success (text answer + return code 0).
- **AC4 (US4)**: Documentation explicitly states no Hugging Face credentials required; tests succeed on machines lacking `HUGGINGFACEHUB_API_TOKEN` environment variable.
- **AC5 (US5)**: Dependency list stays constrained (baseline: `langchain`, `docling`, vector store backend, PDF parsing lib, CLI helpers); `uv.lock` resolves without optional extras, and configuration (env vars, JSON, or CLI flags) described in `feature1_impl_notes.md` or README snippet.
- **AC6 (Quality)**: Logging/errors provide actionable context if the PDF path is missing, unreadable, or question text is blank; exit codes reflect success/failure for automation.

## External Dependencies & Assumptions
- **uv** (Rust-based package/dependency manager) installed locally; instructions will assume `uv` available.
- **LangChain + Docling** libraries supply PDF ingestion + RAG primitives; confirm compatible versions before locking dependencies.
- **Vector store backend**: Use an in-process option (e.g., `FAISS`, `Chroma`, or Docling’s default) that does not require external services.
- **Embedding model**: Choose a local/offline embedding provider packaged with LangChain (e.g., `HuggingFaceEmbeddings` pointing to a model downloadable without auth, or `SentenceTransformers`); ensure licensing allows bundling.
- **Dummy PDF asset**: Provide sourced or auto-generated PDF with harmless content; confirm redistribution rights.
- **Runtime resources**: Pipeline should execute on typical developer laptop (<=16GB RAM) without GPU assumption.
- **Future integrations**: Downstream tasks (architecture, design, implementation, testing, QA) will reference this doc for scope; any new requirements must be appended here before development proceeds.

## Open Questions / Follow-ups
1. Preferred embedding model for offline use? (Need confirmation to balance accuracy vs. size.)
2. Should CLI support batch mode (multiple PDFs / queries) or only single-run scenario? (Current requirement assumes single file + single question.)
3. Are there branding/documentation updates required outside `output/41` (e.g., repo README) after CLI exists?
