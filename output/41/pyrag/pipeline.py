"""Implementation of the LangChain-inspired RAG pipeline."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from . import chunker, doc_loader, embed, logging as log_utils, vectorstore
from .config import PipelineConfig, resolve_cache_paths
from .types import Document, PipelineResult


class PipelineRuntimeError(RuntimeError):
    pass


def execute(config: PipelineConfig) -> PipelineResult:
    resolve_cache_paths(config)
    log_utils.log_stage("pipeline", "start", query=config.query)

    diagnostics: Dict[str, Any] = {"config": config.as_dict()}

    start = time.perf_counter()
    documents = _run_doc_loader(config, diagnostics)
    chunks = chunker.chunk_documents(documents, config.chunk_size, config.chunk_overlap)
    diagnostics["chunk_count"] = len(chunks)
    _maybe_persist_chunks(config, chunks)

    embedder = embed.build_embeddings(config.embedding_model, config.cache_dir)
    store = vectorstore.build_vectorstore(
        embedder,
        chunks,
        persist_path=config.vectorstore_path if config.persist_index else None,
    )
    retriever = vectorstore.get_retriever(store, embedder, k=config.k)
    retrieved = retriever.get_relevant_documents(config.query)

    answer, fallback = _generate_answer(config, retrieved)

    diagnostics.update(
        {
            "retrieved": len(retrieved),
            "fallback": fallback,
            "elapsed_seconds": round(time.perf_counter() - start, 2),
        }
    )

    result = PipelineResult(
        answer=answer,
        context=retrieved,
        fallback_used=fallback,
        diagnostics=diagnostics,
    )
    log_utils.log_stage("pipeline", "end", diagnostics=diagnostics)
    return result


def _run_doc_loader(
    config: PipelineConfig, diagnostics: Dict[str, Any]
) -> List[Document]:
    try:
        documents = doc_loader.load_pdf(config.pdf_path)
    except doc_loader.DocumentLoadError as exc:
        raise PipelineRuntimeError(str(exc)) from exc
    diagnostics["pages"] = len(documents)
    return documents


def _maybe_persist_chunks(config: PipelineConfig, chunks: List[Document]) -> None:
    if not (config.persist_chunks and config.chunk_cache_path):
        return
    payload = [
        {"metadata": chunk.metadata, "page_content": chunk.page_content}
        for chunk in chunks
    ]
    config.chunk_cache_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _generate_answer(
    config: PipelineConfig, documents: List[Document]
) -> tuple[str, bool]:
    if not documents:
        return ("No relevant context was found in the supplied PDF.", True)

    sentences: List[str] = []
    for doc in documents:
        sentences.extend(_sentence_split(doc.page_content))

    query_lower = config.query.lower()
    highlights = [s for s in sentences if query_lower in s.lower()]
    if not highlights:
        highlights = sentences[:3]

    summary = " ".join(highlights)[:1000]
    answer = (
        "Based on the retrieved PDF context, here is a concise response: "
        f"{summary.strip()}"
    )
    fallback = config.llm_backend == "context-only"
    return answer, fallback


def _sentence_split(text: str) -> List[str]:
    tokens = [segment.strip() for segment in text.replace("\n", " ").split(".")]
    return [segment for segment in tokens if segment]


def format_answer(result: PipelineResult) -> str:
    context_lines = [
        f"- Page {doc.metadata.get('page', '?')}: {doc.metadata.get('source')}"
        for doc in result.context
    ]
    context_block = "\n".join(context_lines) if context_lines else "(no context)"
    return (
        f"Answer:\n{result.answer}\n\n"
        f"Fallback used: {result.fallback_used}\n"
        f"Context:\n{context_block}\n"
    )
