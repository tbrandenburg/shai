# Feature 3 – Environment Requirements

## Objective
- Collapse the external configuration surface so that only nine vetted environment variables remain user-facing while every other setting is enforced internally by the `pyrag` package.
- Preserve the Feature 2 loader→chunker→embedder→storage→search pipeline behavior (`uv run pyrag`) and keep linting/testing guarantees intact as called out in `uv_requirements.md` and `rag_requirements.md`.
- Provide a single source of truth for `.env.example`, `pyrag/config.py`, and downstream architecture/design docs so subsequent phases cannot re‑introduce ad-hoc variables.

## Inputs & Traceability
- Issue context and stakeholder directive to "heavily reduce" env vars (`issue_conversation.md`).
- Packaging scope/acceptance criteria (`uv_requirements.md`).
- Modular pipeline requirements (`rag_requirements.md`) and design blueprint (`rag_design.md`).
- Current `.env.example` plus parsing rules in `pyrag/config.py`.

## Approved External Variables
Only the variables below may appear in `.env.example`, be parsed inside `pyrag/config.py`, or be referenced in docs/CLI help. All names are uppercase with snake_case, mirroring existing usage.

| Name | Default | Acceptable Range / Format | Validation & Fallbacks | Module Owner | Business Rationale |
| --- | --- | --- | --- | --- | --- |
| `DOC_CACHE_DIR` | `.pyrag_cache` | Relative or absolute path writable by the CLI; must resolve on local filesystem. | Config creates the directory if missing; failure if path exists but is not writable. | Loader / Pipeline infra | Keeps the only file-path knob user-facing so large Docling PDFs can be cached wherever storage policies allow. |
| `MILVUS_URI` | *(empty)* | Blank or URI pointing to Milvus Lite (`file://`), local socket, or remote Milvus endpoint. | Blank ⇒ pipeline provisions a temp Milvus Lite path inside `DOC_CACHE_DIR`; custom URIs validated for supported schemes before storage init. | Storage module | The lone connectivity control users still need (per `rag_architecture.md`), allowing BYO Milvus while defaulting to self-managed Lite. |
| `MILVUS_COLLECTION` | `pyrag_docs` | Alphanumeric plus underscores, ≤ 64 chars. | Validation enforces regex `^[A-Za-z0-9_]+$`; invalid values fall back to default and trigger a warning in CLI logs. | Storage module | Lets advanced users isolate datasets without editing code while guarding naming hygiene. |
| `TOP_K` | `5` | Integer 1–20 (recommended upper bound keeps retrieval latency acceptable). | Config casts to `int`, ensures `≥ 1`; values >20 log a warning but cap at 20 to avoid runaway costs. | Search / Validation | Directly controls retrieved answer breadth; still crucial for experimentation and aligns with FR-R2/FR-V1. |
| `CHUNK_SIZE` | `1000` | Integer 200–2000 tokens/characters. | Must be `> 0`; enforced to remain `> CHUNK_OVERLAP`; values outside range clamped with warning. | Chunker | Operators occasionally adjust chunk sizing for corpora, so this remains tunable for Docling/HybridChunker parity. |
| `CHUNK_OVERLAP` | `200` | Integer 0–(CHUNK_SIZE − 1). | Validation ensures non-negative, `< CHUNK_SIZE`; invalid entries revert to default 200. | Chunker | Governs continuity between chunks; keeping it configurable preserves recall tuning without exposing every chunker knob. |
| `LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Case-insensitive. | Invalid values default to `INFO` while emitting a warning; CLI prints the active level at startup. | Pipeline logging (`pyrag/logging.py`) | Provides the single permitted observability setting to match PEP8/Ruff-friendly logging discipline. |
| `VALIDATION_ENABLED` | `true` | Boolean strings `{true,false,1,0,yes,no,on,off}`. | Parsed once; defaults to `true`. When set `false`, CLI logs a warning and skips `pyrag.validation.validate`. | Validation module | Keeps governance knob for CI and smoke tests while enabling future task-machine stages to toggle validation only when necessary. |
| `METRICS_VERBOSE` | `false` | Same boolean parsing as above. | When `true`, modules emit extended metrics tables; when `false`, only summaries appear. Default `false` protects readability. | Pipeline / Observability | Allows advanced operators to request richer telemetry without reintroducing dozens of bespoke env vars. |

### Additional Notes
- All numeric fields will raise `ValueError` before pipeline start if parsing fails, ensuring `.env` mistakes surface before resource-intensive stages run (aligning with `pyrag/config.py` behavior).
- `.env.example` must list only the rows above, in the order shown, each with inline comments describing purpose/expected range.
- Typer CLI help and README configuration sections must mirror this table to remain contractually consistent.

## Internalized / Derived Settings
The following legacy environment variables are now **internal-only**. Implementers must hard-code these defaults inside `pyrag/config.py` (or compute them from the remaining nine variables) and remove them from `.env.example`. Any overrides must flow through future CLI options or developer-only hooks, not public env vars.

| Legacy Variable(s) | Handling Strategy | Default / Source | Notes & Owning Module |
| --- | --- | --- | --- |
| `SOURCE_URL` | Constant inside `PipelineSettings`; override requires code change or future CLI flag reserved for maintainers. | `https://arxiv.org/pdf/2408.09869` (Docling Technical Report). | Keeps loader deterministic and prevents users from pointing at arbitrary PDFs without design review, per `rag_requirements.md` FR-L1. |
| `EXPORT_TYPE` | Locked to `ExportType.DOC_CHUNKS`. | `DOC_CHUNKS`. | Aligns with architecture expectation that DOC_CHUNKS remains default; alternate modes now require code-level change vetted by architects. |
| `SOURCE_HEADERS` | Derived from a curated allowlist inside loader (likely empty). | `{}` by default. | Prevents misconfigured auth headers; loader may still compute headers when DOC_CACHE_DIR indicates cached copy. |
| `QUERY_TEXT` | Embedded in `PipelineSettings` default question; future customization handled via CLI option rather than env var. | "Which are the main AI models in Docling?" | Maintains reproducible validation metrics requested in Feature 2 QA. |
| `HF_TOKEN` / generation model knobs | Removed from public config; CLI will auto-detect token from system key store or treat generation as optional, always avoiding crashes when absent. | `None`. | Issue #42 explicitly says no HuggingFace token required; keeping it internal avoids recurring support tickets. |
| `PROMPT`, `GEN_MODEL_ID`, LangChain chain params | Codified inside `pyrag/search.py` defaults. | Values from current implementation (PromptTemplate, `mistralai/Mistral-7B-Instruct-v0.2`). | Maintains parity with Feature 2 while ensuring search pipeline changes go through code review rather than ops tweaks. |
| `INDEX_TYPE`, `METRIC_TYPE`, other Milvus tunables | Stored as constants within `pyrag/storage.py` (e.g., `FLAT`, `COSINE`). | Derived from design blueprint. | Eliminates misalignment between QA and prod by freezing storage topology unless architects explicitly change it. |
| Test/CI toggles (e.g., `PYRAG_TEST_MODE`) | Internal to pytest fixtures or Typer options; not documented to end users. | Managed by tests. | Prevents confusion for CLI operators while retaining developer ergonomics inside `tests/`. |

## Governance & Validation Rules
- `pyrag/config.py` must be updated so `PipelineSettings.from_env()` only inspects the nine approved variable names; any other keys are ignored with a debug log for traceability.
- `.env.example`, README, and Typer help text must stay synchronized with this document. Any future env addition requires updating this file first and re-running the Feature 3 pipeline gates.
- Feature 3 QA will verify:
  1. Setting each numeric/boolean variable to out-of-range values triggers the documented validation behavior (clamp, warning, or hard fail) while `uv run pyrag` exits non-zero for fatal misconfigurations.
  2. `env_requirements.md` → `env_architecture.md` → `env_design.md` traceability remains intact (each doc must cite the previous one).
  3. Build/test logs (`env_build_log.md`, `env_test_results.md`) explicitly reference changes to `.env.example` and `pyrag/config.py` to prove compliance.
- Module owners listed above are accountable for documenting how their component interprets the variable during architecture/design/implementation phases.

## Next Steps for Downstream Agents
1. Architecture phase (`env_architecture.md`) should describe how configuration is loaded from `.env` → Typer overrides → internal defaults while respecting the narrowed surface and secret-handling guidance for `MILVUS_URI`.
2. Design phase must specify precise edits to `.env.example`, `pyrag/config.py`, `pyrag/pipeline.py`, and documentation to implement these requirements.
3. Implementation/testing phases must log all configuration-related commands inside `env_build_log.md`/`env_test_results.md` for auditability.
