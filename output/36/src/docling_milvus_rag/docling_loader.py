"""PDF ingestion utilities built around Docling with offline fallbacks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .cache import Cache, NoOpCache

try:  # pragma: no cover - optional dependency
    from docling.document_converter import DocumentConverter
    from docling_core.types import DoclingDocument
except Exception:  # pragma: no cover - docling not available during tests
    DocumentConverter = None  # type: ignore[assignment]
    DoclingDocument = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from pypdf import PdfReader
except Exception:  # pragma: no cover - fallback path
    PdfReader = None  # type: ignore[assignment]


@dataclass
class RawDoc:
    """Normalized document representation emitted by the ingestor."""

    doc_id: str
    page: int
    text: str
    metadata: dict[str, str]


class DoclingIngestor:
    """Load PDFs via Docling when available or fall back to PyPDF."""

    def __init__(self, cache: Cache | None = None) -> None:
        self.cache = cache or NoOpCache()

    def ingest(self, pdf_paths: Iterable[Path]) -> list[RawDoc]:
        documents: list[RawDoc] = []
        for path in pdf_paths:
            hashed = _hash_file(path)
            cached = self.cache.read(hashed)
            if cached:
                documents.extend(RawDoc(**entry) for entry in cached)
                continue
            doc_entries = self._ingest_single(path, hashed)
            documents.extend(doc_entries)
            self.cache.write(hashed, [entry.__dict__ for entry in doc_entries])
        return documents

    def _ingest_single(self, path: Path, doc_id: str) -> list[RawDoc]:
        if DocumentConverter is not None:
            return self._ingest_with_docling(path, doc_id)
        if PdfReader is not None:
            return self._ingest_with_pypdf(path, doc_id)
        raise RuntimeError("Neither docling nor pypdf is installed; cannot ingest PDFs")

    def _ingest_with_docling(self, path: Path, doc_id: str) -> list[RawDoc]:
        assert DocumentConverter is not None  # for mypy
        converter = DocumentConverter()
        doc: DoclingDocument = converter.convert(path)  # type: ignore[call-arg]
        outputs: list[RawDoc] = []
        for page_idx, page in enumerate(doc.pages, start=1):
            text = page.text or ""
            outputs.append(
                RawDoc(
                    doc_id=doc_id,
                    page=page_idx,
                    text=text.strip(),
                    metadata={
                        "source": path.name,
                        "page_number": str(page_idx),
                    },
                )
            )
        if not outputs:
            outputs.append(
                RawDoc(
                    doc_id=doc_id,
                    page=1,
                    text=str(doc.export_to_markdown()),
                    metadata={"source": path.name},
                )
            )
        return outputs

    def _ingest_with_pypdf(self, path: Path, doc_id: str) -> list[RawDoc]:
        assert PdfReader is not None
        reader = PdfReader(str(path))
        outputs: list[RawDoc] = []
        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            outputs.append(
                RawDoc(
                    doc_id=doc_id,
                    page=page_idx,
                    text=text.strip(),
                    metadata={
                        "source": path.name,
                        "page_number": str(page_idx),
                    },
                )
            )
        return outputs


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
