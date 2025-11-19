# Feature 1 – Architecture Blueprint

## Objective & Scope
Convert the LangChain Docling RAG Colab notebook into a uv-managed CLI (`uv run pyrag`) that ingests a local PDF (dummy fixture by default), runs a lightweight offline RAG stack, and answers a single natural-language question without requiring Hugging Face tokens or external services.

## System Context
- **Invocation**: `uv run pyrag --pdf <path> --query <text> [--chunk-size 750 --chunk-overlap 100 --embedding-model all-MiniLM-L6-v2]`
- **Runtime envelope**: CPU-only developer laptops (≤16 GB RAM), offline after dependencies installed.
- **Primary libraries**: LangChain core, Docling PDF loader/chunker, FAISS or Chroma in-memory vector store, SentenceTransformers embeddings downloaded once, standard Python logging/typer (or click) for CLI.
- **Artifacts**: Input PDF, chunk metadata, embedding vectors, serialized vector store cache (optional), textual answer/log file (optional future enhancement).

## End-to-End RAG Flow
1. **CLI Entrypoint (`pyrag.__main__`)**
   - Parse CLI args, validate PDF path/query presence, expose configuration defaults from `pyproject.toml`/`uv.lock` dependencies.
   - Initialize logging + structured diagnostics for downstream QA (AC6).
2. **Document Ingestion (`doc_loader.py`)**
   - Use Docling/DoclingLangChain loader to read the PDF into text blocks with layout awareness.
   - Normalize metadata (page numbers, section titles) and emit a plain-text corpus for chunking.
3. **Chunking (`chunker.py` or pipeline helper)**
   - Apply LangChain `RecursiveCharacterTextSplitter` (configurable chunk size/overlap) to produce deterministic chunks for the dummy PDF.
   - Persist chunked documents in memory and optionally under `.uv-cache/pyrag/chunks.json` for inspection.
4. **Embedding (`embed.py`)**
   - Instantiate SentenceTransformers or other offline embedding class (LangChain `HuggingFaceEmbeddings` pointing to a local model path) triggered via uv-installed weights.
   - Ensure model download occurs during first run and is cached locally (documented path) to satisfy offline runs.
5. **Vector Store (`vectorstore.py`)**
   - Load FAISS/Chroma in-memory store, ingest chunk embeddings, optionally export to `/tmp/pyrag_index.faiss` for reuse.
   - Provide retriever interface with `k` parameter (default 4) and score threshold.
6. **Query Handling & Retrieval (`pipeline.py`)**
   - Embed the user query, retrieve top-k chunks, and hand them to LangChain QA chain (e.g., `RetrievalQA` with `load_qa_chain` using an LLM that works offline such as `GPT4All` or local `llama.cpp` binding, or fallback to `llama-cpp-python`).
   - Given constraints, prefer `local LLM (e.g., `gpt4all-falcon`)` or, if too heavy, implement summary by feeding retrieved chunks into an extraction template answered by `langchain.llms.Ollama` or offline `LlamaCpp` configured with manageable weights.
7. **Answer Synthesis & Output**
   - Format final answer with cited chunk metadata, print to stdout, and optionally emit JSON (for automation) under `--output-json path` (future extension).
   - Exit code 0 on success; non-zero for validation failures or pipeline errors.

## Runtime Resources & Operational Notes
- **Memory**: <2 GB for embeddings + vector store on dummy PDFs; streaming ingestion avoids loading entire large PDFs simultaneously.
- **Storage**: Temporary FAISS index ≤50 MB; cached SentenceTransformer weights ~90 MB; both stored under uv cache dir.
- **Performance**: Expect <10s cold start (model download) and <2s warm runs for dummy PDF.
- **Observability**: Python logging with INFO default, DEBUG option via `--verbose`; include elapsed time per stage for diagnostics.

## Data Artifacts
| Stage | Artifact | Location | Retention |
| --- | --- | --- | --- |
| Ingestion | Raw PDF | user-provided path / `tests/fixtures/dummy.pdf` | Input only |
| Chunking | Chunk list JSON (optional) | `.uv-cache/pyrag/chunks.json` | Overwrite per run |
| Embedding | Model weights | `~/.cache/huggingface/` or uv-managed cache | Persist between runs |
| Vector Store | FAISS index | `/tmp/pyrag_index.faiss` | Ephemeral unless `--persist` flag |
| QA Output | Text/JSON answer | stdout / optional file | Controlled by CLI |

## Fallback & Resilience Behaviors
- **Embedding fallback**: If preferred model unavailable, fall back to `sentence-transformers/paraphrase-MiniLM-L3-v2` auto-downloaded; warn user.
- **Retriever fallback**: If FAISS initialization fails, switch to LangChain `Chroma` in-memory backend without persistence.
- **LLM fallback**: If offline LLM weights missing, degrade to `langchain.llms.OpenAI` _only_ when `OPENAI_API_KEY` is set, otherwise return retrieved context-only answer (concatenate top chunks) to stay token-free.
- **Validation errors**: Missing PDF/query produce exit code 2 with actionable message; unreadable PDF triggers docling parse fallback to PyPDFLoader; chunk/embedding exceptions trigger cleanup + suggestion to delete cache.

## uv Project Integration
- `pyproject.toml` declares minimal dependencies (`langchain`, `docling`, `sentence-transformers`, `faiss-cpu`, `click`/`typer`, `pypdf` fallback) and console script entry `pyrag = pyrag.__main__:cli`.
- `uv.lock` pins versions for reproducibility; instructions in README emphasize `uv sync` then `uv run pyrag ...`.
- Optional `[tool.uv.workspace]` metadata to ensure pyrag package recognized; tests located under `tests/` executed via `uv run pytest` once added.

## Security & Compliance Considerations
- No secrets required; ensure code checks `os.environ` for HF tokens only to warn if unused.
- Validate file paths to avoid directory traversal or network fetches.
- Document licensing for bundled models; prefer MIT/Apache assets (e.g., MiniLM family).

## Next Steps & Hand-offs
- Backend developer uses this blueprint to design concrete modules (`pyrag/doc_loader.py`, `pyrag/embed.py`, `pyrag/pipeline.py`, CLI wiring) with config surfaces + logging hooks referenced above.
- Implementation must document any deviations (e.g., specific LLM choice) in `feature1_impl_notes.md` for QA traceability.
