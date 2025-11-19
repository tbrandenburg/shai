## Context
- The Docling-based UV project now needs Feature 3: collapse the configuration surface so only the nine explicit environment variables (DOC_CACHE_DIR, MILVUS_URI, MILVUS_COLLECTION, TOP_K, CHUNK_SIZE, CHUNK_OVERLAP, LOG_LEVEL, VALIDATION_ENABLED, METRICS_VERBOSE) remain public while the rest become internal defaults managed by the `pyrag` package.
- Implementation must stay aligned with the existing loader→chunker→embedder→storage→search pipeline, keep `uv run pyrag` as the single entrypoint, and ensure PEP8/Ruff compliance plus regression-proof validation via pytest and CLI smoke tests.
- Deliverables will mirror the Task Machine pattern by producing new requirements/architecture/design documents, updating `.env.example`, `pyrag/config.py`, `pyrag/pipeline.py`, related docs, and logging every change/test inside the `output/42/` folder for traceability.

## Role Descriptions
### Role: business-analyst
- Agent Path: .github/agents/08-business-product/business-analyst.md

### Role: platform-engineer
- Agent Path: .github/agents/03-infrastructure/platform-engineer.md

### Role: backend-developer
- Agent Path: .github/agents/01-core-development/backend-developer.md

### Role: test-automator
- Agent Path: .github/agents/04-quality-security/test-automator.md

### Role: error-detective
- Agent Path: .github/agents/04-quality-security/error-detective.md

### Role: project-manager
- Agent Path: .github/agents/08-business-product/project-manager.md

## Chronologic Task List
- [x] [business-analyst] Feature 3 – Config requirements — Read `output/42/issue_conversation.md`, `output/42/uv_requirements.md`, `output/42/rag_requirements.md`, `.env.example`, `output/42/rag_design.md`, and `output/42/pyrag/config.py` to capture why only the nine requested variables should remain externally configurable; document the approved names, defaults, acceptable ranges, validation rules, and module owners inside `output/42/env_requirements.md`, noting which legacy variables become internal constants or derived settings.
  * Summary: Authored `env_requirements.md` with the nine approved env knobs (defaults, ranges, owners) plus a matrix of legacy variables that now become internal constants/derived settings for downstream architecture/design work.
- [x] [platform-engineer] Feature 3 – Config architecture — Using `output/42/env_requirements.md`, `output/42/rag_architecture.md`, and `output/42/rag_design.md`, design how those nine variables flow through loader/chunker/embedder/storage/search modules plus the Typer CLI; save `output/42/env_architecture.md` describing configuration load order (.env → CLI overrides → defaults), secret storage expectations (e.g., MILVUS_URI), fallbacks for unset values, and how configuration objects are injected into `pyrag/pipeline.py`.
  * Summary: Authored `env_architecture.md` capturing load order, secret handling, module injection, and per-variable flow so downstream design can wire the nine approved env knobs without reopening the surface.
- [x] [backend-developer] Feature 3 – Config design — Translate `output/42/env_architecture.md` into a concrete engineering plan inside `output/42/env_design.md` that spells out the exact edits for `.env.example`, `output/42/pyrag/config.py`, `output/42/pyrag/pipeline.py`, `output/42/pyrag/cli.py`, and docs (README + any module docstrings), including dataclass schemas, parsing helpers, logging behavior when defaults are used, and the verification matrix that coders must follow.
  * Summary: Delivered `env_design.md` detailing the new `PipelineSettings` schema, helper/validation flow, CLI override strategy, doc updates, and a verification matrix so implementation/test phases can proceed without re-expanding the env surface.
- [x] [backend-developer] Feature 3 – Config implementation — Follow `output/42/env_design.md` to refactor `.env.example`, the config/dataclass loader, CLI options, and module wiring so that only the nine supported variables are read while all other values are computed internally; update any affected modules/tests (e.g., `pyrag/config.py`, `pyrag/pipeline.py`, `pyrag/search.py`, `pyrag/logging.py`, `README.md`) and capture every command/file touched in `output/42/env_build_log.md`.
  * Summary: Collapsed config surface to the nine governed env vars (.env example, README, config helpers, logging, CLI, pipeline, and tests), recorded work in `env_build_log.md`, and noted that `uv run --project … pytest output/42/tests` currently fails because setuptools sees both `pyrag` and `tmp_cli_debug2` as top-level packages in the flat layout.
- [x] [test-automator] Feature 3 – Config testing — Execute `uv tool run ruff format`, `uv tool run ruff check`, `uv run --extra dev pytest`, and two `uv run pyrag` invocations (one using `.env.example`, another overriding env vars via shell) to confirm the pipeline honors the reduced configuration; summarize timestamps, exit codes, and observed behavior (e.g., log level switching, chunk size respected) inside `output/42/env_test_results.md` while linking back to `output/42/env_build_log.md` for reproducibility.
  * Summary: Captured env_test_results.md showing format pass, Ruff lint failures (B008 + UP035), and setuptools blocking pytest plus both uv runs due to the lingering tmp_cli_debug2 package noted in env_build_log.md.
- [x] [error-detective] Feature 3 – Config defect triage — If `output/42/env_test_results.md` reveals failures or regressions, dig into the implicated modules/logs, patch the configuration code accordingly, rerun only the affected commands, and document root causes, applied fixes, and prevention ideas in `output/42/env_defects.md` (referencing commit hashes or file sections where possible).
  * Summary: Resolved Ruff/import lint, constrained setuptools to the `pyrag` package, pinned Click <8.2 for Typer 0.12.5, restored the `run` subcommand via a callback, reran Ruff/pytest/two `pyrag run` commands, and logged the full root-cause analysis plus prevention steps in `env_defects.md`.
- [x] [project-manager] Feature 3 – Config replanning — Review `output/42/env_test_results.md` and `output/42/env_defects.md`, then append a "Feature 3 Wrap-up" section at the end of `output/42/task_machine_plan.md` summarizing completion status, residual risks (e.g., sensitivity to Milvus URIs), and next-iteration recommendations while keeping prior wrap-up notes intact.
  * Summary: Consolidated the wrap-up section capturing passing lint/tests, remaining Milvus/packaging risks, and forward-looking hardening tasks.

## Feature 3 Wrap-up
- **Completion Status**: Config surface is now limited to the nine governed variables with Ruff, pytest, and both `uv run pyrag` scenarios succeeding after the fixes documented in `output/42/env_defects.md`.
- **Residual Risks**: Milvus connectivity remains sensitive to malformed or unreachable `MILVUS_URI` values, and the `[tool.setuptools] packages = ["pyrag"]` constraint will break if new first-party packages are added without updating the allowlist.
- **Next-Iteration Recommendations**: 1) Add a Milvus reachability probe (mockable in CI) to the smoke tests to fail fast on URI or credential mistakes; 2) automate a packaging guardrail that asserts only approved packages are discoverable before builds; 3) schedule a review of the Typer/Click pin so future upgrades include compatibility validation rather than emergency downgrades.
