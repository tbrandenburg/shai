# Feature 1 – Error Analysis

## Investigation Summary
- Role: error-detective
- Focus: explain recurring warnings during the `uv run pyrag` integration run and assess risk of incorrect fallback reporting.
- Inputs parsed: `feature1_test_report.md`, runtime log capture from a fresh CLI invocation, implementation files under `pyrag/`.

## Observed Symptoms
1. Every execution raises `[WARNING] ... Falling back to hash embeddings: No module named 'sentence_transformers'` even though the pipeline succeeds (`feature1_test_report.md:23-32`).
2. CLI output always ends with `Fallback used: True`, suggesting degraded service even when full retrieval and answer synthesis succeed.

## Reproduction Evidence
- Command: `uv run pyrag --pdf tests/fixtures/dummy.pdf --query "LangChain" --verbose`
- Log excerpt (2025-11-19 20:06:59 UTC):
```
[INFO] pipeline start {'query': 'LangChain'}
[WARNING] Falling back to hash embeddings: No module named 'sentence_transformers'
[INFO] pipeline end {'pages': 1, 'chunk_count': 1, 'retrieved': 1, 'fallback': True, 'elapsed_seconds': 0.04}
Fallback used: True
```

## Root Cause Analysis
### RC1 – Optional dependency omission triggers warning on every run
- `pyrag/embed.py:71-77` first attempts to initialize `SentenceTransformerWrapper`; because `sentence_transformers` is intentionally excluded from the uv lock to satisfy the lightweight/offline requirement, import always fails, raising `EmbeddingInitError` and logging the warning.
- Impact: warning log becomes noise, masking future embedding failures and lowering trust. Accuracy is limited to hash embeddings, which diverges from LangChain parity.

### RC2 – Misleading `fallback_used` flag definition
- In `pyrag/pipeline.py:82-104`, `_generate_answer` unconditionally sets `fallback = config.llm_backend == "context-only"`; the CLI prints this flag as "Fallback used" regardless of whether any degradation occurred.
- Impact: Operators interpret the output as a runtime failure when it actually represents the intentional context-only summarizer. Downstream alerting could false-positive on every run.

## Impact Assessment
- **User-facing:** Perceived instability because both the logger and CLI declare "fallback" paths even on clean runs.
- **Quality:** Hard to detect real regressions in embeddings or answer generation while warnings remain constant.
- **Performance/Accuracy:** Hash embeddings provide deterministic but low-fidelity vectors, so semantic retrieval quality degrades for anything beyond the dummy PDF.

## Mitigation & Recommendations
1. Ship an optional "enhanced" dependency extra (`pip install .[embeddings]`) or documented toggle that installs `sentence-transformers` when networked environments allow it; until then, downgrade the warning to `INFO` once the fallback is expected via config flag.
2. Introduce a dedicated `diagnostics.embedding_backend` field plus CLI output such as `Embedding backend: hash (fallback)` and reserve warnings for unexpected failures (e.g., cache corruption).
3. Rename or restructure the `fallback_used` flag to differentiate "LLM backend = context-only" from actual runtime fallbacks. Example: `llm_backend="context-only"` or `synthesizer_mode="template"` so monitoring hooks can reason on intent.
4. Add a negative-path test that intentionally installs `sentence-transformers` (perhaps via local extra) to ensure the primary embedding path still works when available, preventing silent drift.

## Prevention & Monitoring Improvements
- Extend telemetry to emit structured diagnostics (`diagnostics["embedding_fallback"] = True/False`) and push them to log aggregation so alerts can be keyed off unexpected True values.
- Track cache directory size and load time metrics once real embeddings are enabled to catch resource exhaustion before deployment.
- Document in the CLI notes that `Fallback used: True` currently indicates context-only summarization, and schedule backlog work (see project-manager task) to eliminate the ambiguity.
