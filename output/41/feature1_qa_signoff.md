# Feature 1 – QA Signoff

## Inputs Reviewed
- Requirements trace: `feature1_requirements.md`
- Architecture/design/implementation notes: `feature1_architecture.md`, `feature1_design.md`, `feature1_impl_notes.md`, CLI notes
- Source modules under `pyrag/`, automated tests in `tests/test_pyrag_dummy_pdf.py`, and execution evidence inside `feature1_test_report.md`

## Acceptance Criteria Verification
| AC | Description | Evidence | Status |
| --- | --- | --- | --- |
| AC1 | Notebook logic converted to runnable CLI using dummy PDF | `uv run pyrag --pdf tests/fixtures/dummy.pdf --query "LangChain"` succeeds (test report) and modules `pyrag/pipeline.py`, `pyrag/doc_loader.py`, `pyrag/chunker.py` orchestrate ingestion→answer flow | ✅ Pass |
| AC2 | CLI exposed through uv with documented flags | `pyproject.toml` registers `[project.scripts] pyrag`, `pyrag/__main__.py` implements argparse CLI with PDF/query/chunking/verbosity flags, CLI notes document usage | ✅ Pass |
| AC3 | Dummy PDF fixture documented + used in automation | Fixture at `tests/fixtures/dummy.pdf` referenced by CLI defaults and pytest suite; CLI notes highlight default path | ✅ Pass |
| AC4 | Offline execution without Hugging Face token | `pyrag/embed.py` falls back to deterministic hash embeddings when `sentence_transformers` unavailable, log snippet confirms fallback without token | ✅ Pass |
| AC5 | Lightweight dependencies and uv lock coverage | `pyproject.toml` limits runtime deps to `pypdf`; configuration details + caches documented in implementation notes/CLI notes | ✅ Pass |
| AC6 | Actionable logging + error handling | `pyrag/config.py` raises `InvalidConfigError` for missing files, CLI prints errors with exit code 2; verbose logging + log-file flag recorded in CLI notes and logs | ✅ Pass |

## Coverage & Metrics
- Automated suite: 2 CLI integration tests (100% pass) validating default and verbose paths (`uv run pytest -q`).
- Functional areas exercised: PDF ingestion, embedding fallback telemetry, answer formatting, CLI exit codes.
- Gaps: No negative-path automation (missing PDF, invalid query), no persistence toggles, no performance or multi-document scenarios. Manual spot-check performed for config/logging code to confirm graceful failures exist but remain untested.

## Defects & Risks
- **Open Risk – Limited scenario coverage:** Only happy-path CLI tests exist; risk of regressions around error handling, alternate flags, and cache persistence remains medium.
- **Observation – External embeddings optionality:** When `sentence_transformers` is installed offline, caching path may grow large; document storage impact for ops teams.
- No blocking defects observed; CLI honors acceptance criteria and logs clearly for QA consumption.

## Release Recommendation
**Conditional Go.** Current build satisfies all acceptance criteria and passes regression tests, but release should be paired with follow-up work to automate failure-path cases and persistence toggles to raise confidence beyond the current 2-test coverage.
