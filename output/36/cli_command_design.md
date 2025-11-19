# CLI Command Design — `docling-milvus-rag`

## 1. Developer Experience Guardrails
- Single-entry Typer app exposed as `docling-milvus-rag` via `[project.scripts]`.
- Startup < 50 ms for argument parsing by deferring heavy imports until pipeline invocation.
- Deterministic exit codes: `0` success, `2` validation (bad args, missing files), `3` runtime pipeline errors, `4` store/caching maintenance failures.
- Offline-first defaults: embedded dummy PDF (`fixtures/dummy.pdf`), Milvus Lite path under `.cache/milvus_lite/docling.db`, cached embedding + LLM weights validated before execution.
- Observability: structured `structlog` output with context-rich markers plus optional rich status panels when `--verbose`.

## 2. Command Tree Overview
```
docling-milvus-rag [GLOBAL OPTIONS]
├─ run        # default when no subcommand is provided; executes Docling→Milvus pipeline
├─ preflight  # lightweight environment diagnostics & dependency checks
└─ store      # vector store utilities (future-safe grouping)
   ├─ store wipe      # delete or reset Milvus Lite collection(s)
   └─ store inspect   # list stored collections, chunk counts, and metadata
```
- `run` remains the canonical workflow and is aliased to the root command via Typer callback.
- `preflight` shares validators with `run --dry-run` but skips PDF ingestion entirely; intended for CI readiness checks.
- `store` namespace is optional in v1 but keeps room for maintenance actions without polluting top-level flags.

## 3. Global CLI Conventions
- Implemented with Typer + Rich to unlock grouped help text, syntax highlighting, and progress indicators.
- Config resolution order: `config/defaults.toml` → env vars (`DOCMILVUS_*`) → CLI flags. Resolved configuration echoed when `--verbose` or `DOCMILVUS_DEBUG=1`.
- Shared global options available to every subcommand:
  - `--config FILE`: override defaults file (env: `DOCMILVUS_CONFIG`).
  - `--log-level [critical|error|warning|info|debug]` (env: `DOCMILVUS_LOG_LEVEL`, default `info`).
  - `--json-logs / --no-json-logs` (env: `DOCMILVUS_JSON_LOGS`, default `False`).
  - `--verbose`: enable Rich status + additional validation traces.
  - `--version`: print CLI + backend version, exits immediately.

## 4. `run` Command Specification
| Flag / Arg | Env Var | Type / Default | Notes |
| --- | --- | --- | --- |
| `--pdf PATH ...` (supports multiple) | `DOCMILVUS_PDFS` (comma-separated) | `List[Path]`, default `fixtures/dummy.pdf` | Validates existence; when missing uses bundled dummy PDF and logs warning. Multi-doc ingestion concatenates chunk streams.
| `--export-type [chunks|markdown]` | `DOCMILVUS_EXPORT_TYPE` | `str`, default `chunks` | Passed to Docling export; validation ensures supported enum.
| `--question TEXT` | `DOCMILVUS_QUESTION` | `str`, default "Summarize the dummy PDF" | Required for answer generation; fallback question ensures success path.
| `--top-k INTEGER` | `DOCMILVUS_TOP_K` | `int`, default `4` | Must be >=1 and <=50; influences retrieval breadth.
| `--chunk-size INTEGER` | `DOCMILVUS_CHUNK_SIZE` | `int`, default from defaults.toml (e.g., 1500) | Optional override; ensures > chunk_overlap.
| `--chunk-overlap INTEGER` | `DOCMILVUS_CHUNK_OVERLAP` | `int`, default 200 | Validator ensures `< chunk_size`.
| `--milvus-uri TEXT` | `DOCMILVUS_MILVUS_URI` | `str`, default `.cache/milvus_lite/docling.db` | Automatically expands `~`, ensures parent dir exists; warns when remote URI given offline.
| `--collection TEXT` | `DOCMILVUS_COLLECTION` | `str`, default `docling_{pdfstem}_{timestamp}` | Accepts explicit name to allow re-use.
| `--embedding-model TEXT` | `DOCMILVUS_EMBEDDING_MODEL` | `str`, default `all-MiniLM-L6-v2` (local) | Pre-run check ensures weights on disk; prompts instructions otherwise.
| `--llm-backend [local-llama|stub]` | `DOCMILVUS_LLM_BACKEND` | `str`, default `local-llama` | `stub` option short-circuits to deterministic canned response for CI.
| `--output FILE` | `DOCMILVUS_OUTPUT` | `Path`, optional | Writes JSON report; ensures parent folder exists and never overwrites without prompt unless `--force`.
| `--force` | `DOCMILVUS_FORCE` | bool, default `False` | Allows overwriting output file or re-initializing Milvus collection.
| `--dry-run` | `DOCMILVUS_DRY_RUN` | bool, default `False` | Executes validators + configuration echo only; exit code `0` if clean, `2` on validation failure.

### `run` Execution Flow
1. Parse + validate arguments, resolving config layering.
2. `validate_documents()` ensures each PDF exists; if none provided uses dummy fixture and logs `PIPELINE_DOC_DEFAULT` info.
3. `ensure_models_cached()` checks embedding + LLM weights, pointing to README instructions on miss.
4. Build pipeline configuration dataclass; optionally print sanitized config when `--verbose`.
5. Invoke `DoclingPipeline().run(config)`; stream progress (ingestion, chunking, Milvus inserts, retrieval, answer) via Rich status columns.
6. Emit summary block: answer text, retrieval hits, Milvus collection path, runtime duration.
7. Write JSON artifact when `--output` and include location in logs.
8. Return exit codes above.

## 5. `preflight` Command
- Purpose: Fast diagnostics for CI/local readiness.
- Options: inherits global options plus `--full` (runs Docling import in dry-run), `--checks [env|models|milvus|files|all]` to scope validations.
- Output: table summarizing Python version, UV sync status, required files, Milvus directory permissions, cached models. Non-zero exit when any check fails.
- Implementation detail: uses same validator functions as `run --dry-run`, ensuring parity; prints remediation tips (e.g., `uv run python scripts/prefetch_models.py`).

## 6. `store` Subcommands
- `store wipe`
  - Flags: `--collection TEXT` (required unless `--all`), `--all` to drop every collection for the configured Milvus URI, `--force` to skip confirmation.
  - Validations: prompts unless `--force`; ensures path exists; warns when offline store not found.
- `store inspect`
  - Flags: `--collection TEXT` optional; when omitted lists all collections with chunk counts and last-ingested timestamps.
  - Output: Rich table plus optional JSON via `--output` (shares option from run).
- Both reuse `--milvus-uri`, `--log-level`, etc., guaranteeing consistent environment detection.

## 7. Environment Variable Matrix
| Env Var | Targets | Description |
| --- | --- | --- |
| `DOCMILVUS_PDFS` | run | Comma-separated list of PDF paths; parsed before CLI args for headless automation.
| `DOCMILVUS_EXPORT_TYPE` | run | Sets default export mode.
| `DOCMILVUS_MILVUS_URI` | run, store | Points to Milvus Lite DB/URI.
| `DOCMILVUS_COLLECTION` | run, store | Sets default collection name/selector.
| `DOCMILVUS_QUESTION` | run | Default inference question.
| `DOCMILVUS_TOP_K`, `DOCMILVUS_CHUNK_SIZE`, `DOCMILVUS_CHUNK_OVERLAP` | run | Retrieval tuning knobs.
| `DOCMILVUS_EMBEDDING_MODEL`, `DOCMILVUS_LLM_BACKEND` | run | Model/back-end selectors.
| `DOCMILVUS_OUTPUT`, `DOCMILVUS_FORCE`, `DOCMILVUS_DRY_RUN` | run, store (force) | Output + override behaviors.
| `DOCMILVUS_LOG_LEVEL`, `DOCMILVUS_JSON_LOGS`, `DOCMILVUS_VERBOSE` | global | Logging mode controls.
| `DOCMILVUS_CONFIG` | global | Custom defaults file path.

## 8. Help Text Structure (Typer/Rich)
```
Usage: uv run docling-milvus-rag [OPTIONS] [run|preflight|store]

Summary:
  Offline Docling → Milvus RAG runner that ingests local PDFs, embeds them,
  and answers questions with cached models.

Documents:
  --pdf PATH              One or more PDF files (default: fixtures/dummy.pdf)
  --export-type [chunks|markdown]

Retrieval:
  --question TEXT         Prompt asked of retrieved context (default: Summarize...)
  --top-k INTEGER         Number of context chunks to retrieve (default: 4)
  --chunk-size INTEGER
  --chunk-overlap INTEGER

Vector Store:
  --milvus-uri TEXT       Milvus Lite path or URI (default: .cache/milvus_lite/...)
  --collection TEXT

Output:
  --output FILE           Save JSON transcript of the run
  --log-level ...         {critical,error,warning,info,debug}
  --json-logs / --no-json-logs

Diagnostics:
  --dry-run               Validate inputs without executing pipeline
  --verbose               Show resolved config + progress indicators
  --version               Print CLI version and exit
```
- Help text intentionally capped at <80 lines with logical grouping per requirement.

## 9. Result & Dummy PDF Handling
- Document path resolution order: CLI args > env > defaults; fallback automatically appends `fixtures/dummy.pdf` if resulting list empty.
- `validate_dummy_pdf()` ensures the bundled file exists; if missing, surfaces actionable error (likely repo corruption) with `uv sync --fixtures` remediation.
- Pipeline summary includes `Document sources` line enumerating resolved files and indicates when dummy was injected (e.g., `[default] fixtures/dummy.pdf`).
- When extra docs provided, CLI warns if duplicates/wildcards resolved to zero matches; exit code `2` prevents silent failures.
- Output JSON includes `documents` array with `path`, `checksum`, and `source` metadata, empowering QA diffing.

## 10. Usage Examples (for README & Tests)
1. **Baseline offline validation**
   ```bash
   uv run docling-milvus-rag
   ```
   Prints minimal summary plus answer, storing Milvus Lite artifacts under `.cache/`.
2. **Custom analyst question with JSON export**
   ```bash
   uv run docling-milvus-rag --pdf docs/manual.pdf --question "List key compliance steps" --top-k 6 --output runs/manual.json
   ```
   Validates manual path, widens retrieval, writes JSON artifact.
3. **CI preflight without heavy execution**
   ```bash
   uv run docling-milvus-rag preflight --checks all
   uv run docling-milvus-rag --dry-run --milvus-uri /tmp/milvus_ci
   ```
   Ensures environment readiness and deterministic exit codes for automation.

## 11. Next Implementation Steps
- Scaffold Typer app with command tree + shared `@app.callback` to route bare invocation to `run`.
- Implement validator helpers shared across `run`, `preflight`, and `store` subcommands.
- Wire CLI options to `ConfigBuilder`/pipeline modules documented in `rag_module_design.md`.
- Extend README with `Usage` + `Examples` mirroring sections above and mention `uv run docling-milvus-rag --help` for the grouped output.
