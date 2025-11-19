# Feature 3 – Config Design

## Traceability
- **Upstream artifacts**: `env_requirements.md` (single env surface), `env_architecture.md` (load order + flow), Task Machine plan (Feature 3 tasks).
- **Downstream owners**: `.env.example`, `pyrag/config.py`, `pyrag/cli.py`, `pyrag/pipeline.py`, README + CLI/docstrings, build/test evidence captured in `env_build_log.md` and `env_test_results.md`.
- **Scope guardrails**: retain loader→chunker→embedder→storage→search topology and keep `uv run pyrag` as the canonical entrypoint while the nine env knobs remain the only user-visible configuration.

## Objectives & Constraints
1. Collapse configuration parsing so only the approved nine env variables are inspected while every legacy knob becomes an internal constant or derived field.
2. Centralize defaults/validation in `pyrag/config.py`, expose Typer overrides for parity, and emit deterministic logging whenever defaults or clamps are applied.
3. Ensure CLI/docs/.env remain contractually consistent (same order, same descriptions) and document the verification steps future agents must execute.
4. Preserve security posture: `MILVUS_URI` is the lone secret-like field; sanitized snapshots must never leak credentials.

## Data Model & Validation
### PipelineSettings schema
`PipelineSettings` will continue to own both public knobs and derived internal fields but will split them into explicit sections for readability/testing:

| Field | Source | Notes |
| --- | --- | --- |
| `doc_cache_dir: Path` | Env/CLI default `.pyrag_cache` | Created eagerly with `mkdir(parents=True, exist_ok=True)`; validation ensures writability. |
| `milvus_uri: str` | Env/CLI or derived `file://` path | Blank values resolve to `<doc_cache_dir>/milvus-lite` with a `file://` prefix; stored URI always canonicalized. |
| `milvus_collection: str` | Env/CLI default `pyrag_docs` | Regex enforced (`^[A-Za-z0-9_]{1,64}$`); invalid names revert to default + warning. |
| `top_k: int` | Env/CLI default `5` | Parsed via shared helper; values clamped `1..20`. |
| `chunk_size: int` | Env/CLI default `1000` | Valid range `200..2000`; invalid input clamped, warning logged. |
| `chunk_overlap: int` | Env/CLI default `200` | Must satisfy `0 ≤ overlap < chunk_size`; if violation occurs, revert to default and raise `ValueError` when still invalid. |
| `log_level: str` | Env/CLI default `INFO` | Parsed case-insensitively to logging enum; invalid input falls back to INFO with warning. |
| `validation_enabled: bool` | Env/CLI default `true` | Shared bool parser accepts `{true,false,1,0,yes,no,on,off}`; invalid input raises `ValueError`. |
| `metrics_verbose: bool` | Env/CLI default `false` | Same parser as above.
| **Derived/internal** | **Constant** | `source_url`, `export_type`, `headers`, `query_text`, `hf_token`, storage/index knobs, prompt/model IDs become module-level constants referenced by `PipelineSettings` but never by env parsing. |

### Parsing + validation flow
1. `load_settings(overrides: Mapping[str, str] | None = None)` becomes the single public entrypoint.
2. `_collect_env()` uses `dotenv_values()` + `os.environ` but filters to the nine sanctioned keys; unknown keys emit `logger.debug` entries and are dropped.
3. CLI converts Typer overrides into the same mapping so precedence is `.env` → process env → CLI overrides → defaults.
4. Shared helpers enforce types/ranges:
   - `_parse_bool(name, raw, default)` raising `ValueError` for unsupported strings.
   - `_parse_int(name, raw, *, minimum, maximum, clamp_behavior)` returning `(value, used_default: bool)` so logging can mention clamps.
   - `_resolve_doc_cache_dir(raw)` ensuring directories exist and are writable.
   - `_resolve_milvus_uri(raw, cache_dir)` returning canonical URI + flag when derived.
   - `_coerce_log_level(raw)` mapping to `logging` levels.
5. Whenever a helper falls back to a default (e.g., invalid `MILVUS_COLLECTION`), `pyrag.logging.get_logger(__name__)` logs a warning that includes the env key, offending value, and replacement.
6. `PipelineSettings.ensure_valid()` remains but is trimmed to invariants that cannot be clamped (e.g., `chunk_overlap ≥ chunk_size`).

## File-by-File Implementation Plan
### `.env.example`
- Replace current 13-key template with only the nine approved variables, preserving order from `env_requirements.md`.
- For each key, add inline comments describing purpose, range, and default (e.g., `# Writable folder for Docling cache (default: .pyrag_cache)`).
- Document that `MILVUS_URI` can be left blank to auto-provision Milvus Lite under `DOC_CACHE_DIR`.
- Add header block referencing `env_requirements.md` so CI can diff.

### `pyrag/config.py`
- Introduce `CONFIG_KEYS = (<nine names>)` constant and `ConfigDefaults` dataclass containing the authoritative default values (pulled from `env_requirements.md`).
- Refactor `PipelineSettings` to explicitly list only the nine env-facing fields plus derived constants (source URL, export type, headers, query text, HF token placeholder, storage defaults). Derived values move to top-level constants (e.g., `DEFAULT_SOURCE_URL`).
- Replace `_merge_env` with `_collect_env(source_overrides)` that:
  1. Loads `.env` via `dotenv_values()` within `load_settings()`.
  2. Starts from OS env, overlays CLI overrides, and discards unknown keys.
  3. Returns both the filtered mapping and a list of ignored keys for debug logging.
- Implement helper functions described above; unit-testable pure functions live near the bottom of `config.py`.
- Centralize Milvus Lite URI derivation in `_resolve_milvus_uri`; when a blank URI is encountered, create `<doc_cache_dir>/milvus-lite` (if missing) and return `f"file://{path}"`.
- Add `ConfigLogger` warnings when values are clamped: e.g., `_parse_int("TOP_K", raw, min=1, max=20)` logs `"TOP_K=25 exceeds max 20; using 20"`.
- Add `PipelineSettings.snapshot()` to redact secrets (`MILVUS_URI` only reveals scheme/host but hides credentials by replacing anything after `@` with `***`).
- Add `emit_settings_snapshot(settings)` helper that `cli.py` and tests can reuse.
- Update module docstrings to state that only nine env vars are supported.

### `pyrag/cli.py`
- Add Typer options mirroring each env key (e.g., `--doc-cache-dir`, `--milvus-uri`, etc.), defaulting to `None`. When provided, convert to strings and pass into `load_settings(overrides)`.
- After calling `_hydrate_environment`, call `configure_logging(settings.log_level)` (new function exported from `pyrag.logging`).
- Render sanitized snapshot via `emit_settings_snapshot` right after settings load; highlight when defaults were used (`"doc_cache_dir" source="default"`).
- Update CLI help strings to point operators to `.env.example`/README for the definitive variable list.
- Ensure `typer.Exit(code=1)` is raised when validation toggles are off but CLI cannot skip? (Already handled; simply log when validation disabled.)

### `pyrag/pipeline.py`
- Accept the fact that `PipelineSettings` now contains fully resolved values; runner should never re-read env vars.
- Thread `settings.metrics_verbose` through the `_capture_stage` helper (already stored); only change is to emit additional `logger.debug` metrics when verbose flag is true.
- When storage stage returns handles, merge `settings_snapshot` referencing resolved `milvus_uri` so `env_test_results.md` can cite it.
- Add docstring/comments noting the config injection contract mandated by `env_architecture.md`.

### `pyrag/logging.py`
- Expand module with `def configure(level: str) -> None` that normalizes the log level (INFO fallback) and updates the root logger. CLI calls this before printing the snapshot so `LOG_LEVEL=DEBUG` takes effect globally.
- Provide helper `def redact_uri(uri: str | None) -> str` reused by `PipelineSettings.snapshot()`.

### Docs (README, module docstrings)
- Replace the Configuration table with a two-column table listing only the nine variables, their meaning, and default/range statements consistent with `env_requirements.md`.
- Mention CLI overrides in the Usage section (sample command `uv run pyrag -- --top-k 10 --metrics-verbose true`).
- Update `pyrag/config.PipelineSettings` docstring plus CLI help strings to explicitly mention that all other former env vars are now fixed internal defaults.
- Ensure `.env.example`, README, Typer help, and `env_requirements.md` share the same ordering to satisfy the governance hook (document this in README).

## Logging & Telemetry Behavior
- `pyrag/config` logs at INFO when directories are created and WARN when raw inputs are rejected; when defaults are used silently (e.g., values omitted), DEBUG-level statements record the fallback.
- CLI prints a sanitized table (Rich) summarizing the nine active knobs, explicitly marking derived values with `(default)` badges to aid `env_build_log.md` authors.
- When `METRICS_VERBOSE=true`, `PipelineRunner` prints per-stage histograms/extra metadata by serializing `summary.metrics[name]` with `console.log`.

## Verification Matrix
| Scenario | Command(s) | Expected Output / Evidence |
| --- | --- | --- |
| Default `.env` run | `cp .env.example .env`; `uv run pyrag` | CLI logs indicate directory creation, Milvus Lite auto URI, validation passes; snapshot stored in `env_test_results.md` referencing defaults. |
| CLI override precedence | `uv run pyrag -- --top-k 12 --log-level debug` | Snapshot shows `top_k=12`, `log_level=DEBUG`, `METRICS_VERBOSE` unchanged; logs confirm DEBUG verbosity. |
| Invalid numeric clamp | Set `CHUNK_SIZE=50` in `.env`; run CLI | Process exits non-zero if invariant broken (chunk_size <= overlap), otherwise warns and clamps to 200; expectation recorded in `env_test_results.md`. |
| Boolean parsing | `VALIDATION_ENABLED=off`, `METRICS_VERBOSE=on` | Snapshot shows toggled booleans, CLI prints warning that validation disabled. |
| Milvus URI derivation | leave `MILVUS_URI` blank, custom `DOC_CACHE_DIR=/tmp/pyrag-cache` | Storage metrics show derived `file:///tmp/pyrag-cache/milvus-lite`; README instructions validated. |
| Unknown env ignored | Add `FOO=bar` to `.env`; run CLI | No failure; DEBUG log "Ignoring unsupported env var FOO" ensures backward compatibility traceability.

These design decisions align with `env_architecture.md` by keeping configuration centralized, auditable, and limited to the nine approved variables while documenting the precise code/doc changes the implementation agent must follow.
