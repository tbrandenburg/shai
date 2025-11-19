# Feature 1 – Implementation Notes (Python Expert)

## Source Files
- `pyrag/__init__.py`: exposes the public surface (`PipelineConfig`, `load_config`, `execute`, `format_answer`).
- `pyrag/config.py`: dataclass-based config loader that merges CLI args + env vars, enforces PDF existence, and provisions cache folders under `.uv-cache/pyrag/`.
- `pyrag/logging.py`: lightweight structured logging helpers; `configure_logging` wires stream/file handlers, `log_stage` emits json-friendly entries.
- `pyrag/types.py`: local equivalents for LangChain's `Document` and a `PipelineResult` container so downstream modules stay dependency-free.
- `pyrag/doc_loader.py`: PDF ingestion with `pypdf` primary, transparent fallback to raw UTF-8 decoding for environments lacking extras.
- `pyrag/chunker.py`: deterministic chunking with overlap awareness; preserves metadata for downstream citations.
- `pyrag/embed.py`: attempts to boot a `sentence-transformers` model but falls back to a deterministic hash-based embedding that never touches Hugging Face services.
- `pyrag/vectorstore.py`: minimal cosine-similarity store that can persist chunk metadata to JSON when `--persist-index` is enabled.
- `pyrag/pipeline.py`: orchestration of load → chunk → embed → retrieve → summarize, plus chunk/index persistence hooks and human-readable formatter.
- `pyrag/__main__.py`: Typer-forward CLI with argparse fallback so `uv run pyrag --query ...` works even when Typer is missing.

## Key Decisions
1. **Offline guarantee:** replaced remote dependency assumptions with hash-based embeddings and sentence-level summarization so the CLI answers questions without any API tokens. If `sentence-transformers` happens to be installed, it is used automatically.
2. **Graceful degradation:** doc loading, embeddings, and CLI layers each try "full" implementations first and fall back to simpler ones (PyPDF → raw bytes, Typer → argparse). This keeps the runtime resilient across uv sandboxes.
3. **Config validation:** `load_config` now acts as the single truth for defaults, env overrides, and cache path derivation. All modules accept a `PipelineConfig`, preventing hidden global state.
4. **Persistence knobs:** chunk and vectorstore persistence writes JSON payloads into `.uv-cache/pyrag/` so later roles can inspect artifacts without needing FAISS binaries.
5. **Answer synthesis:** until an offline LLM is introduced, the pipeline summarizes the highest-scoring sentences mentioning the query tokens and flags the execution as a fallback in diagnostics.
6. **Diagnostics surface:** every pipeline run returns a `PipelineResult` with structured measurements (pages, chunk counts, elapsed seconds, fallback flag) to ease upcoming QA/test automation work.

## Deviations & Follow-ups
- The hash embedding/vector store pairing is intentionally simple; once a lightweight FAISS/Chroma backend is added, swap `vectorstore.py` accordingly while keeping the same interface.
- No external logging frameworks were added—`logging` + JSON payloads cover the immediate need; upgrade to `structlog` only if richer formatting is required.
- Tests and uv metadata will be handled by subsequent roles per the plan.
