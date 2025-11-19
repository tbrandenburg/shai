# CLI Requirements Brief — `docling-milvus-rag`

## Objective
Deliver a UV-managed command (`uv run docling-milvus-rag`) that reproduces the Docling→Milvus RAG pipeline offline, guiding users through predictable flags for document sources, Milvus persistence, and output handling while maintaining the "very simple" ethos requested by stakeholders.

## Stakeholders & Personas
- **Project sponsor (@tbrandenburg):** Needs a frictionless proof-of-value run that validates Docling→Milvus with one dummy PDF and no HuggingFace tokens.
- **Developers/ML engineers:** Expect configurable knobs (question, top-k, embedding model) for iteration without editing code.
- **QA / Operators:** Require deterministic defaults, observable logs, and scriptable exit codes to integrate into CI smoke tests.

## Environmental Assumptions
- Executed via UV (`uv sync`, `uv run ...`) with dependencies locked in `pyproject.toml` + `uv.lock`.
- Offline execution: all models are locally available or cached prior to runtime; no HuggingFace token or remote Milvus server required.
- Dummy PDF bundled under `fixtures/dummy.pdf` and used when no document path is provided.

## Functional CLI Requirements
1. **Single entry command**
   - Invoke as `uv run docling-milvus-rag [options]` from repo root.
   - CLI must validate environment (Python version, UV sync) and fail fast with actionable error messages.
2. **Document source controls**
   - `--pdf PATH` (default: `fixtures/dummy.pdf`). Accept multiple values or comma-separated list to support future multi-doc ingestion.
   - Provide `--export-type {chunks,markdown}` aligning with Docling `ExportType` choices, default `chunks`.
3. **Milvus persistence options**
   - `--milvus-uri PATH_OR_URI` defaulting to local Lite/sqlite path under `.cache/milvus_lite/`. CLI must create the path if missing and log its location.
   - Optional `--collection` flag for advanced users; default collection name derived from PDF stem + timestamp.
4. **Retrieval and question parameters**
   - `--question TEXT` defaulting to a baked-in validation question (e.g., "Summarize the dummy PDF"), ensuring pipeline completes without additional input.
   - `--top-k INT` (default 4) to control retrieval breadth.
   - `--chunk-size INT` and `--chunk-overlap INT` (optional) surfaced from backend config file for fine-grained tuning.
5. **Embedding/LLM selection**
   - `--embedding-model NAME` defaulting to the lightweight model shipped in project assets; CLI must warn if requested model lacks cached weights.
   - `--llm-backend {local-llama,stub}` or similar switch controlling offline answer generation mode.
6. **Output formatting & logging**
   - Standard console output prints answer text plus provenance snippet (source doc + page) and run duration.
   - Structured logs (INFO level by default, toggled via `--log-level`) include ingestion counts, Milvus insert totals, retrieval hits, and any fallbacks triggered.
   - Optional `--output FILE` to dump JSON report (`question`, `answer`, `sources`, `metrics`).
7. **Configuration layering**
   - CLI reads defaults from `pyproject.toml`/`config/defaults.toml`, overridden by env vars (e.g., `DOCMILVUS_MILVUS_URI`) and finally CLI flags.
8. **Error handling & validation**
   - Missing file paths, invalid URIs, or Milvus initialization failures return non-zero exit codes and descriptive messages.
   - Dry-run mode (`--dry-run`) validates arguments without executing the heavy pipeline for CI linting.

## Non-Functional CLI Requirements
- **Simplicity:** Help text (`-h/--help`) under 80 lines, with grouped sections (Documents, Retrieval, Output, Diagnostics).
- **Discoverability:** Examples in README show base command, custom Milvus path, and JSON output usage.
- **Observability:** Logs timestamped with module prefix; QA can grep for `PIPELINE_COMPLETE` marker.
- **Scriptability:** Return code `0` on success, `2` on validation errors, `3` on runtime pipeline failures to aid automation.

## Usage Scenarios
1. **Baseline offline validation**
   - Command: `uv run docling-milvus-rag`
   - Behavior: Uses bundled dummy PDF, default question, auto Milvus Lite path; prints concise answer and inserts ~N chunks.
2. **Custom analyst question + output capture**
   - Command: `uv run docling-milvus-rag --pdf docs/manual.pdf --question "List key compliance steps" --top-k 6 --output runs/manual.json`
   - Behavior: Reads operator-provided PDF, widens retrieval, saves JSON report for audit trail.
3. **CI smoke test of parameter validation**
   - Command: `uv run docling-milvus-rag --dry-run --milvus-uri /tmp/milvus_ci --embedding-model sentence-transformers/all-MiniLM-L6-v2`
   - Behavior: Confirms environment readiness without executing ingestion; ensures failing args block deployment before runtime.

## Acceptance Criteria
- Help text documents every flag above with defaults and examples.
- Running the three scenarios completes as described without editing code/config files.
- CLI emits structured logs showing ingestion, insert, retrieval, and answer events.
- Requirements traceable to FR1–FR7 and NFR1–NFR5 in `rag_requirements.md`.
