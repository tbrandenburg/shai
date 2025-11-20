# Feature 4 – Documentation Refresh

## Overview
The documentation set now reflects the fully reinstated Docling/LangChain pipeline delivered in Feature 4. The README explains how `uv run pyrag run` exercises DoclingLoader, HybridChunker, HuggingFaceEmbeddings, Milvus (Lite or remote), and the HuggingFaceEndpoint-based retrieval chain while preserving the nine-governed environment surface. `.env.example` continues to expose only those sanctioned keys but now calls out offline/validation guidance for the fallback summarizer. `env_requirements.md` provides the authoritative reference tying each env var to the concrete Feature 4 component plus a sample CLI execution trace that QA and downstream agents can reuse.

## Updated Files
- `README.md` – rewrote prerequisites, quick-start flow, configuration table, pipeline overview, and added a sample `uv run pyrag run --validation-enabled false` transcript that shows telemetry rows (Docling strategy, Milvus URI/mode, LLM fallback) produced by the real integrations.
- `.env.example` – renamed to "Feature 4 – Approved configuration surface", clarified that `DOC_CACHE_DIR` now hosts Docling exports + HuggingFace weights, documented how blank `MILVUS_URI` provisions Milvus Lite, and added guidance for toggling `VALIDATION_ENABLED` when HuggingFaceEndpoint is unreachable.
- `env_requirements.md` – retitled for Feature 4, refreshed objectives to emphasize LangChain behavior, expanded the env-variable table with Component/Behavior context, documented internal-only defaults (Docling source URL, HuggingFace repo IDs, Milvus index topology), and embedded the latest CLI telemetry bullets to anchor QA expectations.

## Follow-up Notes
- Future documentation agents should cross-link `lib_test_results.md` once validation data is available so README snippets can cite real test runs.
- When HuggingFaceEndpoint access improves, capture a second sample run showing `LLM Fallback: no` and append it to README/env docs for contrast.
