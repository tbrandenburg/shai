# Modular RAG Test Results — 2025-11-19

## Command Log
| Command | Purpose | Result |
| --- | --- | --- |
| `uv tool run ruff check` | Lint/typing hygiene | Pass — no findings after import cleanup. |
| `uv run --extra dev pytest` | Module + CLI test suite | 7 tests passed in 4.67s covering loader, chunker, embedder, storage, search, pipeline, and Typer CLI flows. |
| `uv run pyrag` | Full CLI smoke run | Completed successfully; rendered summary table with 1 document, 1 chunk, 1 embedding, 1 hit, and Milvus URI `milvus-lite://memory`. |

## Automated Coverage Highlights
- **Loader cache validation:** Ensures `DoclingLoader` writes `docling_source.json` to the configured cache and returns non-empty payloads.
- **Chunker normalization:** Confirms `HybridChunker` emits ordered chunks with DOC_CHUNKS/HYBRID modes and stable metadata.
- **MiniLM embedder fallback:** Forces hash-based encoder to validate deterministic vectors plus query embeddings without HuggingFace auth.
- **Milvus storage + search orchestration:** Persists embeddings, executes cosine-ranked queries, and verifies `LangChainSearch` answer strings include the asked question.
- **CLI regression:** `tests/test_modules.py::test_cli_run_executes_end_to_end` runs the Typer app with an isolated cache dir (`QUERY_TEXT="Summarize the Docling QA pipeline"`) and asserts the rich summary banner plus green completion signal.
- **Pipeline smoke (`tests/test_pipeline.py`):** Validates `PipelineRunner` metrics for docs/chunks/embeddings/search hits using deterministic settings to prove all modules integrate cleanly.

## CLI Sample Output (`uv run pyrag`)
- **Environment:** Defaults from `.env`/settings (doc cache `.pyrag_cache`, `TOP_K=5`).
- **Prompt:** `Which are the main AI models in Docling?`
- **Answer Snippet:** `Retrieved 1 chunks for 'Which are the main AI models in Docling?'. Mean confidence 0.22. Sources: Docling Technical Report placeholder...`
- **Metrics Observed:** documents=1, chunks=1, embeddings=1, hits=1, collection=`pyrag_docs`, Milvus URI `milvus-lite://memory`.

## Notes & Follow-ups
- SentenceTransformer downloads succeed in this environment; tests pin the fallback encoder to keep CI deterministic.
- Validation step continues to enforce minimum counts (≥1 for docs/chunks/embeddings/hits) and surfaces failures via Typer exit code 1.
