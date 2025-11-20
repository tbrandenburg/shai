# Feature 4 – Environment Requirements

## Objective
- Preserve the strict nine-variable contract introduced in Feature 3 while documenting how each setting now drives the reinstated Docling → LangChain → Milvus pipeline implemented in Feature 4.
- Clarify how `.env.example`, `pyrag/config.py`, `README.md`, and CLI help text stay synchronized so operators can run `uv run pyrag run` without guessing about Docling caches, Milvus Lite folders, or HuggingFaceEndpoint behavior.
- Provide a concrete sample run (using `uv run pyrag run --validation-enabled false`) so QA and documentation reviewers can reference the telemetry emitted by the restored LangChain integrations.

## Inputs & Traceability
- Feature 4 requirement/design artifacts: `lib_requirements.md`, `lib_architecture.md`, `lib_design.md`.
- Implementation evidence: `lib_build_log.md`, updated `pyrag/*.py` modules, `tests/*.py`.
- Prior environment governance: `env_architecture.md`, `env_design.md`, `.env.example`.
- Sample CLI execution captured while drafting this update (included below) to anchor telemetry expectations.

## Approved External Variables
Only the variables below may appear in `.env.example`, be parsed by `pyrag/config.py`, or surface in documentation/CLI help. The Module Owner column now references the real Feature 4 components.

| Name | Default | Acceptable Range / Format | Validation & Fallbacks | Module Owner | Feature 4 Behavior |
| --- | --- | --- | --- | --- | --- |
| `DOC_CACHE_DIR` | `.pyrag_cache` | Writable path on the local filesystem. | Created when missing; loader raises if not writable. | Loader / Pipeline infra | Stores Docling-exported JSON, downloaded PDFs, Milvus Lite files, and HuggingFace model weights. |
| `MILVUS_URI` | *(empty)* | Blank or URI pointing to Milvus Lite (`file://`), ipc/tcp URIs, or remote Milvus endpoints. | Blank ⇒ auto-provisioned Milvus Lite path under `DOC_CACHE_DIR`; invalid URIs raise `MilvusConnectionError`. | Storage module | Determines whether LangChain uses embedded Milvus Lite vs. remote Milvus; telemetry records `milvus_mode`. |
| `MILVUS_COLLECTION` | `pyrag_docs` | Alphanumeric with underscores, ≤ 64 chars. | Regex validated; invalid values reset to default with warning. | Storage module | Names the Milvus collection passed to LangChain's `Milvus` vectorstore. |
| `TOP_K` | `5` | Integer 1–20. | Cast-to-int; values outside range clamp and warn. | Search / Validation | Drives retriever `search_kwargs` and validation thresholds for minimum hits. |
| `CHUNK_SIZE` | `1000` | Integer 200–2000. | Enforced to remain `> 0` and `> CHUNK_OVERLAP`; clamp with warning. | Chunker | Controls Docling HybridChunker window length when chunking `DocChunk` payloads. |
| `CHUNK_OVERLAP` | `200` | Integer 0–(CHUNK_SIZE − 1). | Enforced to remain non-negative and `< CHUNK_SIZE`; invalid entries revert to 200. | Chunker | Maintains continuity for Docling/Markdown chunkers; surfaced in chunker metrics. |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL (case-insensitive). | Invalid values fall back to INFO and trigger a warning. | Logging / Pipeline | Feeds `pyrag.logging.configure`, which now formats telemetry dictionaries for Docling/Milvus metadata. |
| `VALIDATION_ENABLED` | `true` | Boolean strings `{true,false,1,0,yes,no,on,off}`. | Parsed once; default true. When false, CLI skips validation but still records metrics. | Validation module | Governs whether LLM fallback is treated as fatal. Feature 4 validation fails when HuggingFaceEndpoint falls back while the flag is true. |
| `METRICS_VERBOSE` | `false` | Same boolean parsing as above. | Adds per-stage telemetry rows when true. | Pipeline / Observability | Surfaces Docling strategy, embedding model/strategy, Milvus URI/redaction, and HuggingFace fallback status. |

## Internalized / Derived Settings
The following values remain internal-only. They are mentioned here for completeness because documentation now references the real LangChain/Docling components they power.

| Legacy Variable(s) | Handling Strategy | Default / Source | Feature 4 Notes |
| --- | --- | --- | --- |
| `SOURCE_URL` | Constant inside `PipelineSettings`. | `https://arxiv.org/pdf/2408.09869`. | Loader downloads this PDF through DoclingLoader, caching JSON under `DOC_CACHE_DIR/docling_source.json`. |
| `EXPORT_TYPE` | Locked to `ExportType.DOC_CHUNKS`. | `DOC_CHUNKS`. | Required by the Docling HybridChunker integration; fallback Markdown splitter still respects chunk size/overlap env knobs. |
| `QUERY_TEXT` | Embedded default question. | "Which are the main AI models in Docling?" | Appears in CLI telemetry; tests override via Typer option rather than env var. |
| HuggingFace tokens/model IDs | Internal to `PipelineSettings`. | Model defaults: `sentence-transformers/all-MiniLM-L6-v2` (embeddings) and `mistralai/Mistral-7B-Instruct-v0.2` (LLM). | Feature 4 search pipeline instantiates HuggingFaceEndpoint without requiring a token; fallback summarizer runs when the endpoint is unreachable. |
| Milvus index settings | Hard-coded constants. | `FLAT` index, cosine metric. | Documented in `lib_design.md`; sanitized values appear in CLI metrics but have no env knobs. |

## Governance & Validation Rules
1. `.env.example`, `README.md`, CLI help, and this document must continue to describe the exact same nine-variable surface.
2. When QA enables `VALIDATION_ENABLED=true`, they expect Docling loader strategy `docling`, embedding strategy `huggingface`, and search fallback `false`. Any fallback flips validation to non-zero exit, so documentation must instruct operators to disable validation when intentionally running offline.
3. Documentation engineers must cite this file when describing configuration in other artifacts (e.g., `lib_docs.md`).

## Sample Execution Trace
To capture the telemetry emitted by the real pipeline, run:

```
uv run pyrag run --validation-enabled false
```

The 2025-11-20 run produced:

- Loader: `strategy=docling`, 1 document cached under `.pyrag_cache`.
- Chunker: 1 chunk via Docling HybridChunker (strategy `docling`).
- Embedder: `sentence-transformers/all-MiniLM-L6-v2`, `strategy=huggingface`.
- Storage: Milvus Lite at `file://.../.pyrag_cache/milvus-lite`, mode `lite`, collection `pyrag_docs`.
- Search: HuggingFaceEndpoint fallback triggered (`LLM Fallback: yes`), producing a deterministic `(degraded)` answer while still listing sources.
- Validation: skipped (flag false); when true, fallback would raise `ValidationError` instructing the operator to re-run with a reachable HuggingFaceEndpoint or to disable validation explicitly.

Use this trace when updating README snippets, env documentation, or future QA guides so every reference shares a consistent, validated source of truth.
