# Feature 3 – Config Architecture

## Traceability
- Source requirements: `env_requirements.md` (single-digit env surface), `rag_architecture.md` (loader→chunker→embedder→storage→search topology), `rag_design.md` (PipelineSettings + module contracts).
- Target artifacts: `.env.example`, `pyrag/config.py`, `pyrag/cli.py`, `pyrag/pipeline.py`, downstream design (`env_design.md`) and implementation logs/tests.

## Configuration Stack & Load Order
1. **`.env` ingestion** – `pyrag.config.load_settings()` invokes `python-dotenv` against the workspace root, scoping keys to the nine approved variables. Unknown keys are ignored with a DEBUG log to preserve backward compatibility without reopening the surface.
2. **Typer CLI overrides** – CLI options (future-friendly flags such as `--top-k`, `--log-level`) override `.env` values inside `PipelineSettings`. CLI must validate inputs using the same rules as `from_env()` so that overrides remain deterministic.
3. **Internal defaults** – If a value remains unset after steps 1–2, internal defaults from `env_requirements.md` are applied just before constructing `PipelineSettings`. Defaults are centralized in `pyrag/config.py` so `.env.example`, docs, and runtime share a single truth. Derived/legacy knobs (SOURCE_URL, EXPORT_TYPE, QUERY_TEXT, etc.) are injected here as constants or computed fields, never as env parameters.

Settings resolution emits a sanitized snapshot (paths, booleans, ints) through `pyrag.logging` so operators can confirm the active configuration without leaking secrets.

## Secrets & Sensitive Values
- `MILVUS_URI` is treated as the only secret-like field. When blank, `MilvusStore` is instructed to instantiate Milvus Lite under `<DOC_CACHE_DIR>/milvus-lite`, and the resolved URI is injected back into the `PipelineSettings` instance before module wiring.
- Non-empty URIs are validated for approved schemes (`file://`, `tcp://`, `http(s)://`). Invalid URIs trigger a fatal configuration error before any storage work starts to avoid corrupting collections.
- No other public env vars hold credentials; HuggingFace tokens and headers remain internalized per `env_requirements.md`.

## Configuration Object Lifecycle
- `PipelineSettings` (defined in `pyrag/config.py`) carries only the nine external knobs plus derived/internal fields. Its `from_env()` factory applies validation, clamps values (TOP_K ≤ 20, CHUNK_SIZE/CHUNK_OVERLAP ranges), and materializes booleans using the shared parser.
- `pyrag/cli.py` calls `load_settings()` once, prints the sanitized snapshot, and passes the immutable settings object into `PipelineRunner`.
- `pyrag/pipeline.py` threads `settings` through each stage without re-reading env vars. Module constructors accept only the specific fields they need, keeping wiring explicit and testable.

## Variable Flow Through Modules
| Variable | Consuming Layers | Flow Details |
| --- | --- | --- |
| `DOC_CACHE_DIR` | Config → Loader → Storage | Config ensures the directory exists. Loader caches Docling artifacts here; storage reuses the path for Milvus Lite scratch space when `MILVUS_URI` is blank. |
| `MILVUS_URI` | Config → Storage → Search | Blank value replaced with auto-generated Lite URI. Storage creation logs the resolved URI, while Search embeds it inside `RunSummary` for observability. |
| `MILVUS_COLLECTION` | Config → Storage | Validated via regex; storage uses it to idempotently create collections. Invalid names revert to default and emit a warning before storage init continues. |
| `TOP_K` | Config → Search → Validation | Clamped between 1 and 20; Search uses it for retrieval breadth and records the effective value in metrics. Validation asserts `search_result.top_k ≥ settings.top_k`. |
| `CHUNK_SIZE` | Config → Chunker | Enforced to exceed `CHUNK_OVERLAP`; chunker receives both settings and logs the actual size applied (post-clamp) for QA traceability. |
| `CHUNK_OVERLAP` | Config → Chunker | Must remain `< CHUNK_SIZE`; invalid entries revert to default 200 and trigger a warning prior to chunking. |
| `LOG_LEVEL` | Config → Logging subsystem | Parsed case-insensitively. `pyrag.logging.configure(level)` runs before CLI output to ensure consistent verbosity across modules. |
| `VALIDATION_ENABLED` | Config → Validation gate → PipelineRunner | When `false`, `PipelineRunner` skips `validation.validate()` but emits a WARN banner so test automation can detect deviations. |
| `METRICS_VERBOSE` | Config → Loader/Chunker/Embedder/Storage/Search | Enables per-stage detailed metric tables. Modules inspect this flag to decide whether to emit extended telemetry (e.g., chunk distribution histograms). |

## Fallbacks & Error Handling
- **Path issues**: Non-writable `DOC_CACHE_DIR` raises a configuration error with remediation instructions. Pipeline stops before loader spins up Docling.
- **Invalid numerics**: Parsing failures raise `ValueError`. Range violations trigger clamp + warning (non-fatal) except when resulting config would violate invariants (`CHUNK_OVERLAP ≥ CHUNK_SIZE` → hard fail).
- **Boolean parsing**: Shared helper accepts `{true,false,1,0,yes,no,on,off}`; ambiguous strings raise errors at config load time so behavior never differs between CLI and tests.
- **Secret absence**: Missing `MILVUS_URI` never fails; missing derived/internal secrets are impossible because they are constants embedded within `pyrag`.

## Injection into Pipeline Runner
- `PipelineRunner` is the single consumer of `PipelineSettings`. Upon initialization it:
  1. Instantiates `DoclingLoader`, `HybridChunker`, `MiniLMEmbedder`, `MilvusStore`, and `LangChainSearch`, passing only the settings fields each module requires.
  2. Registers a teardown callback from `MilvusStore` that relies on the resolved `milvus_uri` (generated or provided) and `doc_cache_dir` for cleanup.
  3. Captures `RunSummary.settings_snapshot` so QA artifacts (`env_build_log.md`, `env_test_results.md`) can reference the exact configuration used.
- CLI smoke tests and `uv run pyrag` both rely on this injection order to guarantee that no module re-reads env vars or consults OS state directly.

## Governance Hooks
- Architecture mandates that `.env.example`, Typer help output, and README config tables list the nine variables **in the same order** shown above. Platform tooling can diff these files against `env_requirements.md` to detect drift.
- Future CLI options must route through the same validation helpers before mutating `PipelineSettings` to preserve a single authoritative pipeline contract.
- Storage of plan/test evidence: `env_build_log.md` must reference every command that mutated configuration files, and `env_test_results.md` must cite the sanitized snapshot emitted at runtime for reproducibility.

This configuration architecture ensures the UV Docling pipeline exposes only the sanctioned knobs, maintains deterministic defaults, and injects settings through a single orchestrator boundary so downstream design/implementation phases can proceed without re-litigating the configuration surface.