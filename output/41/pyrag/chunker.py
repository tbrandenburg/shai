"""Deterministic chunking utilities."""

from __future__ import annotations

from typing import List

from .types import Document


def chunk_documents(
    documents: List[Document], chunk_size: int, chunk_overlap: int
) -> List[Document]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap >= chunk_size:
        chunk_overlap = int(chunk_size * 0.2)

    chunks: List[Document] = []
    for doc in documents:
        text = doc.page_content
        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end]
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = chunk_index
            metadata["offset"] = start
            chunks.append(Document(page_content=chunk_text, metadata=metadata))
            if end == len(text):
                break
            start = max(0, end - chunk_overlap)
            chunk_index += 1
    return chunks or documents
