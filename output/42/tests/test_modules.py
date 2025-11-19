"""Module-level QA coverage for the pyrag pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from pyrag.chunker import Chunk, HybridChunker
from pyrag.cli import app
from pyrag.config import ExportType, PipelineSettings
from pyrag.embedder import MiniLMEmbedder
from pyrag.loader import DocChunk, DoclingLoader
from pyrag.search import LangChainSearch
from pyrag.storage import MilvusStore


def _build_settings(tmp_path: Path, *, name: str = "doc_cache") -> PipelineSettings:
    cache_dir = tmp_path / name
    cache_dir.mkdir(exist_ok=True)
    return PipelineSettings(
        doc_cache_dir=cache_dir,
        milvus_uri=f"file://{cache_dir}/milvus-lite",
        milvus_collection="test_collection",
        top_k=2,
        chunk_size=80,
        chunk_overlap=16,
        log_level="INFO",
        validation_enabled=True,
        metrics_verbose=False,
        source_url="https://example.com/docling.pdf",
        export_type=ExportType.DOC_CHUNKS,
        query_text="How does Docling structure documents?",
    )


def _doc_chunk() -> DocChunk:
    text = ("Docling chunk " * 120).strip()
    return DocChunk(
        id="doc-0",
        text=text,
        metadata={"section": "intro", "page": "1"},
        tokens=len(text.split()),
    )


def _force_hash_embeddings(monkeypatch: Any) -> None:
    def _disable_model(self: MiniLMEmbedder, settings: PipelineSettings):  # type: ignore[override]
        return None

    monkeypatch.setattr(MiniLMEmbedder, "_ensure_model", _disable_model, raising=False)


def _as_chunk(doc: DocChunk, index: int = 0) -> Chunk:
    return Chunk(id=f"{doc.id}:{index}", text=doc.text, metadata=doc.metadata, order_index=index)


def test_loader_materializes_cache_and_chunks(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path, name="loader_cache")
    loader = DoclingLoader()
    doc_chunks = loader.load(settings)
    assert doc_chunks, "Loader should yield at least one chunk"
    cache_file = settings.doc_cache_dir / "docling_source.json"
    assert cache_file.exists(), "Cache payload missing"
    assert doc_chunks[0].metadata["source_url"] == settings.source_url


def test_chunker_produces_ordered_hybrid_chunks(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path, name="chunker_cache")
    chunker = HybridChunker()
    chunks = chunker.split([_doc_chunk()], settings)
    assert len(chunks) > 1, "Hybrid chunking should expand long docs"
    assert chunks[0].metadata["doc_id"] == "doc-0"
    assert {chunk.metadata["chunk_mode"] for chunk in chunks} <= {"DOC_CHUNKS", "HYBRID"}


def test_embedder_generates_deterministic_vectors(tmp_path: Path, monkeypatch: Any) -> None:
    _force_hash_embeddings(monkeypatch)
    settings = _build_settings(tmp_path, name="embed_cache")
    chunk = _as_chunk(_doc_chunk())
    embedder = MiniLMEmbedder()
    embeddings = embedder.embed([chunk], settings)
    assert len(embeddings) == 1
    assert len(embeddings[0].vector) == 8
    query_embedding = embedder.embed_query("Docling QA?", settings)
    assert query_embedding.metadata["chunk_id"] == "query"


def test_storage_persist_and_query(tmp_path: Path, monkeypatch: Any) -> None:
    _force_hash_embeddings(monkeypatch)
    settings = _build_settings(tmp_path, name="storage_cache")
    chunk = _as_chunk(_doc_chunk())
    embedder = MiniLMEmbedder()
    embeddings = embedder.embed([chunk], settings)
    store = MilvusStore()
    handle = store.persist(embeddings, settings.milvus_collection)
    ranked = store.query(embeddings[0].vector, top_k=1)
    assert ranked[0][0].metadata["chunk_id"] == chunk.id
    handle.teardown()


def test_search_returns_confident_answer(tmp_path: Path, monkeypatch: Any) -> None:
    _force_hash_embeddings(monkeypatch)
    settings = _build_settings(tmp_path, name="search_cache")
    chunk = _as_chunk(_doc_chunk())
    embedder = MiniLMEmbedder()
    embeddings = embedder.embed([chunk], settings)
    store = MilvusStore()
    handle = store.persist(embeddings, settings.milvus_collection)
    search = LangChainSearch(store, embedder)
    result = search.ask(handle, settings.query_text, settings)
    assert result.sources, "Search should surface at least one source"
    assert settings.query_text.split()[0] in result.answer


def test_cli_run_executes_end_to_end(tmp_path: Path, monkeypatch: Any) -> None:
    _force_hash_embeddings(monkeypatch)
    cache_dir = tmp_path / "cli_cache"
    cache_dir.mkdir(exist_ok=True)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--top-k",
            "2",
            "--metrics-verbose",
            "true",
        ],
        env={
            "DOC_CACHE_DIR": str(cache_dir),
        },
    )
    assert result.exit_code == 0
    assert "Pipeline completed successfully" in result.stdout
