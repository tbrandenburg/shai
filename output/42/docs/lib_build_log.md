# Feature 4 – LangChain Build Log

## 2025-11-20
- Refactored `pyrag/config.py`, `logging.py`, and `exceptions.py` to expose Docling/HuggingFace constants, Milvus mode snapshots, JSON logging, and a dedicated `MilvusConnectionError` for downstream telemetry consumers.
- Replaced the placeholder modules (`loader.py`, `chunker.py`, `embedder.py`, `storage.py`, `search.py`, `pipeline.py`, `validation.py`, `cli.py`) with production-ready integrations that instantiate LangChain Docling loader/splitters, HuggingFace embeddings+endpoint, and Milvus-backed storage while keeping deterministic fallbacks for the task-machine sandbox.
- Updated `.env.example` plus unit tests (`tests/test_modules.py`, `tests/test_pipeline.py`) to exercise the new seams and ensure the hash-based fallbacks keep CI deterministic when HuggingFace or Milvus services are unavailable.
- Documented the dependency and module wiring above so the Documentation and Validation agents can trace the feature implementation without re-deriving the steps.
