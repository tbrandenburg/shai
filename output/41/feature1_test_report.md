# Feature 1 – Test Report

## Scope & Objectives
- Validate the offline RAG CLI exposed via `uv run pyrag` using the bundled dummy PDF (AC1–AC4).
- Ensure verbose logging and fallback behavior remain observable for automation pipelines.

## Test Artifacts
- Fixture: `tests/fixtures/dummy.pdf` (text-based stub with PDF header for deterministic ingestion).
- Automated suite: `tests/test_pyrag_dummy_pdf.py` with two CLI-level regression tests executed through `uv`.

## Execution Summary
| Command | Result |
| --- | --- |
| `uv run pytest -q` | ✅ Pass — 2 tests, 0 failures (runtime ≈0.44s) |
| `uv run pyrag --pdf tests/fixtures/dummy.pdf --query "LangChain" --verbose` | ✅ Pass — emits diagnostics and synthesized answer |

## Key Assertions & Coverage
- CLI exits with code 0, prints `Answer`, `Fallback used`, and `Context` blocks for the default dummy PDF path.
- Verbose mode emits `[INFO]`/`[WARNING]` telemetry confirming fallback to hash embeddings when SentenceTransformers is unavailable.
- Reported context references the dummy PDF ensuring traceability to AC3.

## Log Snippet
```
[INFO] 2025-11-19 20:04:43,378 pipeline start {'query': 'LangChain'}
[WARNING] 2025-11-19 20:04:43,416 Falling back to hash embeddings: No module named 'sentence_transformers'
[INFO] 2025-11-19 20:04:43,416 pipeline end {... 'pages': 1, 'chunk_count': 1, 'retrieved': 1, 'fallback': True, 'elapsed_seconds': 0.04}}
Answer:
Based on the retrieved PDF context, here is a concise response: %PDF-1 4 % Dummy PDF Fixture ...
Fallback used: True
Context:
- Page 0: tests/fixtures/dummy.pdf
```

## Data Handling & Cleanup
- Tests rely on the committed dummy PDF; no runtime files or indexes persisted because defaults keep `persist_index/persist_chunks` disabled.
- `.uv-cache/pyrag` remains populated for faster repeated runs; no cleanup performed per requirement to keep offline caches warm.

## Outstanding Risks
- Coverage currently limited to CLI happy paths; downstream QA/error-detective roles should expand scenarios (missing PDF, chunk persistence toggles, etc.).
