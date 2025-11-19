"""PDF ingestion helpers."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .types import Document


class DocumentLoadError(RuntimeError):
    """Raised when a PDF cannot be read using any backend."""


def load_pdf(path: Path, metadata_only: bool = False) -> List[Document]:
    if not path.is_file():
        raise DocumentLoadError(f"PDF not found: {path}")

    page_text = _load_with_pypdf(path) or _load_as_text(path)
    if not page_text:
        raise DocumentLoadError(f"Failed to extract text from {path}")

    documents: List[Document] = []
    for index, text in enumerate(page_text):
        content = "" if metadata_only else text
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": str(path),
                    "page": index,
                    "bytes": Path(path).stat().st_size,
                },
            )
        )
    return documents


def _load_with_pypdf(path: Path) -> List[str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return []

    texts: List[str] = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            value = page.extract_text() or ""
            texts.append(value.strip())
    except Exception:
        return []
    return texts


def _load_as_text(path: Path) -> List[str]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DocumentLoadError(str(exc)) from exc
    decoded = data.decode("utf-8", errors="ignore")
    return [decoded]
