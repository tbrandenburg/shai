# Docling→Milvus RAG Module Design

## 1. Architectural Overview
- **Goal:** Provide a Python package that ingests local PDFs via Docling, chunks and embeds text using offline-friendly models, persists embeddings into Milvus Lite, and answers questions through a local LLM, all orchestrated via `uv run docling-milvus-rag`.
- **Design Principles:** modular components, deterministic configuration, zero external credentials, log-friendly orchestration, and easy substitution of embeddings/LLM/vector-store implementations.
- **Runtime Target:** Python 3.11 managed by UV; dependencies pinned through `pyproject.toml` + `uv.lock`.

## 2. Proposed Package Layout
```
src/
  docling_milvus_rag/
    __init__.py
    config.py             # Pydantic settings + loaders
    logging.py            # Structured logger factory
    docling_loader.py     # DoclingIngestor implementation
    chunker.py            # ChunkBuilder abstraction using LangChain splitters
    embeddings.py         # EmbeddingService (SentenceTransformers wrapper)
    milvus_store.py       # MilvusStore (Lite + client management)
    retrieval.py          # Retriever logic (vector search + filters)
    llm.py                # AnswerGenerator leveraging llama-cpp
    pipeline.py           # Pipeline orchestrator + metrics aggregation
    cache.py              # (Optional) file-based cache for embeddings/ingestion
    cli.py / __main__.py  # Added later by CLI developer (export Typer app)
```
Supporting assets:
- `config/defaults.toml` – baked-in defaults referenced by `config.py` (optional but recommended for clarity).
- `fixtures/dummy.pdf` – canonical ingestion input for demos/tests.
- `.milvus/` – local directory containing Milvus Lite data (ignored by git).
- `models/` – user-populated directory containing GGUF weights + embedding caches (documented in README).

## 3. Configuration Loading Strategy
1. **Data Models:** Define `AppConfig` (Pydantic BaseModel) capturing document paths, export type, chunk params, embedding + LLM settings, Milvus options, runtime toggles (json logs, cache enabled). Nested models for each subsystem (`MilvusConfig`, `EmbeddingConfig`, `LLMConfig`).
2. **Sources & Precedence:**
   - CLI args (Typer) → highest priority (later CLI task wires these into config factory).
   - Environment variables prefixed `DOCMILVUS_` using `pydantic-settings`.
   - `config/defaults.toml` (bundled for reproducible defaults) loaded via `tomllib`.
   - Hard-coded safe defaults inside `config.py` ensuring minimal runnable config even without files.
3. **Loader API:**
   ```python
   def load_config(cli_args: dict | None = None) -> AppConfig:
       return ConfigBuilder.from_sources(cli_args)
   ```
   - Validates existence of PDF paths (resolve relative to repo root or cwd) and ensures they point to local files.
   - Normalizes `milvus_uri` (default `sqlite:///./.milvus/docling.db`).
   - Expands `models/` relative paths and verifies files when `llm.model_path` is set.
4. **Runtime Exposure:** `pipeline.py` accepts `AppConfig` instance; CLI passes `load_config(vars(args))` to pipeline.

## 4. Component Interfaces
- **DoclingIngestor (`docling_loader.py`)**
  ```python
  class DoclingIngestor:
      def __init__(self, export_type: ExportType, cache: Cache | None = None): ...
      def ingest(self, pdf_paths: Iterable[Path]) -> Iterable[RawDoc]: ...
  ```
  - Uses Docling API mirroring Colab example, but constrained to local file paths.
  - Emits `RawDoc(text: str, metadata: dict)` dataclass with `source`, `page`, `checksum`.

- **ChunkBuilder (`chunker.py`)**
  ```python
  class ChunkBuilder:
      def __init__(self, chunk_size: int, chunk_overlap: int): ...
      def build(self, docs: Iterable[RawDoc]) -> list[Document]: ...
  ```
  - Relies on `RecursiveCharacterTextSplitter`. Adds metadata fields (`doc_id`, `page_range`).

- **EmbeddingService (`embeddings.py`)**
  ```python
  class EmbeddingService:
      def __init__(self, model_name: str, device: str = "cpu", cache: Cache | None = None): ...
      def embed_documents(self, documents: list[Document]) -> EmbeddingBatch:
          return EmbeddingBatch(vectors: np.ndarray, metadocs: list[dict])
      def embed_query(self, text: str) -> list[float]: ...
  ```
  - Wraps `SentenceTransformer` with lazy download to local cache (~`~/.cache/huggingface`). No tokens required.

- **MilvusStore (`milvus_store.py`)**
  ```python
  class MilvusStore:
      def __init__(self, cfg: MilvusConfig, dim: int = 384): ...
      def upsert(self, batch: EmbeddingBatch) -> VectorInsertResult: ...
      def similarity_search(self, query_vector: list[float], top_k: int, filter: dict | None = None) -> list[RetrievedChunk]: ...
      def close(self) -> None: ...
  ```
  - Handles Lite init, collection creation (`docling_chunks`), id generation, and ensures deterministic schema.

- **Retriever (`retrieval.py`)**
  ```python
  class Retriever:
      def __init__(self, store: MilvusStore, embedder: EmbeddingService, top_k: int, score_threshold: float | None = None): ...
      def run(self, question: str, doc_id: str | None = None) -> list[RetrievedChunk]: ...
  ```
  - Optionally filters by `doc_id` derived from PDF filename hash.

- **AnswerGenerator (`llm.py`)**
  ```python
  class AnswerGenerator:
      def __init__(self, cfg: LLMConfig): ...
      def generate(self, question: str, contexts: list[RetrievedChunk]) -> AnswerResult:
          return AnswerResult(answer: str, citations: list[str], metrics: dict)
  ```
  - Uses `llama_cpp.Llama` with local GGUF file; ensures prompts remain within context window.

- **Pipeline (`pipeline.py`)**
  ```python
  class Pipeline:
      def __init__(self, ingestor, chunk_builder, embedder, store, retriever, answerer, logger): ...
      def run(self, config: AppConfig) -> PipelineResult:
          # orchestrate ingestion→chunking→embedding→insert→retrieval→LLM
  ```
  - Responsible for metrics timing, exception handling, and caching decisions.

## 5. Local PDF Ingestion Strategy (No Remote Credentials)
- Accepts only filesystem paths; rejects URLs.
- Validates that each input path exists and has `.pdf` extension (case-insensitive).
- Uses Docling’s offline parsers; fallback to `pypdf` text extraction if Docling fails (ensures pipeline resilience without network).
- Computes file hash to support caching and to partition Milvus collections if necessary.
- Stores derived metadata (`doc_id`, `checksum`, `page_count`) for later filtering.

## 6. Data Contracts & Types
| Artifact | Type | Description |
| --- | --- | --- |
| `RawDoc` | `dataclass` with `doc_id`, `page`, `text`, `metadata` | Output of DoclingIngestor |
| `Document` | LangChain `Document` | Input to embeddings (includes `doc_id`, `chunk_index`, `source`) |
| `EmbeddingBatch` | `namedtuple(vectors: np.ndarray, metadocs: list[dict])` | Carries embeddings + metadata tuples |
| `RetrievedChunk` | `dataclass(text, score, metadata)` | Output of Milvus search |
| `AnswerResult` | `dataclass(answer: str, citations: list[str], metrics: dict)` | Final pipeline output |
| `PipelineResult` | `dataclass(answer: str, metrics: dict, chunks_indexed: int)` | CLI-friendly summary |

## 7. Error Handling & Logging
- Central logger factory in `logging.py` configures `structlog` (JSON optional via config flag).
- Each component raises `PipelineError` subclasses (e.g., `IngestionError`, `EmbeddingError`); pipeline catches, logs, and re-raises for CLI to format user-facing messages.
- Metrics captured per phase: `duration_ms`, `chunk_count`, `vector_count`, `retrieval_latency`, `generation_latency`.

## 8. Offline-First Dependency Notes
- Embedder downloads models via `sentence-transformers` once; document manual download option if machines are air-gapped (preload `models/embeddings`).
- Llama.cpp weights distributed via README instructions; pipeline validates presence and emits actionable error if missing.
- Milvus Lite uses file-based storage under `.milvus/`; ensure directory creation.

## 9. Extension Points
- Future reranker slot: define `Reranker` protocol to plug-in additional scoring without rewriting pipeline.
- Cache provider interface in `cache.py` (default `NoOpCache`) enabling disk caching of embeddings keyed by `doc_id + chunk_hash`.
- Config-driven toggles for `--wipe-store` (drop collection before each run) and `--persist-store` (reuse existing vectors).

This design keeps the backend implementation organized, testable, and aligned with the Docling→Milvus architecture, ensuring later agents can wire the CLI and tests without reorganizing modules.
