"""Integration-style tests for the Docling → Milvus pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from docling_milvus_rag import pipeline
from docling_milvus_rag.docling_loader import DoclingIngestor, RawDoc


@pytest.fixture()
def ensure_dummy_pdf() -> Path:
    pdf_path = PROJECT_ROOT / "fixtures" / "dummy.pdf"
    if not pdf_path.exists():  # pragma: no cover - guard rails for CI environments
        pytest.skip("Dummy PDF not available; pipeline cannot be validated")
    return pdf_path


def test_pipeline_entrypoint_populates_store_and_returns_answer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ensure_dummy_pdf: Path) -> None:
    """Pipeline should ingest, chunk, embed, and answer using offline fallbacks."""

    def fake_ingest(self: DoclingIngestor, pdf_paths):
        docs: list[RawDoc] = []
        for idx, pdf in enumerate(pdf_paths):
            raw_bytes = Path(pdf).read_bytes()
            text = raw_bytes.decode("latin1", errors="ignore") or "No content"
            docs.append(
                RawDoc(
                    doc_id=f"doc-{idx}",
                    page=1,
                    text=text,
                    metadata={"source": Path(pdf).name, "page_number": "1"},
                )
            )
        return docs

    monkeypatch.setattr(DoclingIngestor, "ingest", fake_ingest, raising=False)

    overrides = {
        "pdf_paths": [str(ensure_dummy_pdf)],
        "question": "What is contained inside the dummy PDF?",
        "runtime.cache_dir": str(tmp_path / "cache"),
        "runtime.persist_store": False,
        "milvus.drop_existing": True,
    }

    result = pipeline.run_pipeline(overrides)

    assert result.chunks_indexed > 0, "vector store should receive embedded chunks"
    assert result.answer.strip(), "LLM fallback must emit a textual answer"
    assert "Offline fallback answer" in result.answer or len(result.answer.split()) > 3
    assert result.metrics["duration_sec"] >= 0
