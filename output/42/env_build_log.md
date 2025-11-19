# Feature 3 – Config Build Log

## 2025-11-19
- Ran `rg -n "PipelineSettings" output/42 -g"*.py"` to catalog every module consuming the configuration dataclass before edits.
- Ran `rg -n "milvus_uri" output/42 -g"*.py"` to confirm storage + CLI touchpoints for the Milvus URI changes.
- Trimmed `.env.example` to the nine-governed variables with annotated defaults and ranges, plus README configuration/usage copy to keep the docs contract synchronized.
- Rebuilt `pyrag/config.py` with `ConfigDefaults`, strict env filtering, helper parsers, sanitized snapshots, and the new `emit_settings_snapshot` hook; paired it with the logging, CLI, and pipeline updates (new logging helpers, Typer override plumbing, metrics verbosity, and Milvus URI injection).
- Updated `tests/test_pipeline.py` and `tests/test_modules.py` to rely solely on the supported variables/CLI overrides so regression checks align with the reduced surface.
- Attempted `uv run --project /home/runner/work/shai/shai/output/42 pytest output/42/tests` but the build failed because setuptools discovered both `pyrag` and `tmp_cli_debug2` as top-level packages in the flat layout.
