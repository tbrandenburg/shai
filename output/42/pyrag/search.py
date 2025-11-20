"""Search orchestration built on the embedder + storage modules."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from pyrag.config import PipelineSettings
from pyrag.embedder import EmbedderProtocol
from pyrag.exceptions import SearchError
from pyrag.logging import get_logger, safe_extra
from pyrag.storage import StorageHandle, StorageProtocol

logger = get_logger(__name__)

try:  # pragma: no cover - optional LangChain dependency
    _prompt_module = import_module("langchain.prompts")
    PromptTemplate = getattr(_prompt_module, "PromptTemplate", None)
    _chain_module = import_module("langchain.chains.combine_documents")
    create_stuff_documents_chain = getattr(_chain_module, "create_stuff_documents_chain", None)
    _retrieval_module = import_module("langchain.chains")
    create_retrieval_chain = getattr(_retrieval_module, "create_retrieval_chain", None)
except Exception:  # pragma: no cover - fallback
    PromptTemplate = None  # type: ignore[assignment]
    create_stuff_documents_chain = None  # type: ignore[assignment]
    create_retrieval_chain = None  # type: ignore[assignment]

try:  # pragma: no cover - optional HuggingFace endpoint
    _hf_module = import_module("langchain_huggingface")
    HuggingFaceEndpoint = getattr(_hf_module, "HuggingFaceEndpoint", None)
except Exception:  # pragma: no cover - fallback
    HuggingFaceEndpoint = None  # type: ignore[assignment]


@dataclass(slots=True)
class RetrievedSource:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class SearchResult:
    question: str
    answer: str
    sources: list[RetrievedSource]
    latency_ms: float
    top_k: int
    confidence_scores: list[float]
    fallback_used: bool = False


class SearchOrchestrator:
    def ask(
        self, handle: StorageHandle, query_text: str, settings: PipelineSettings
    ) -> SearchResult:
        raise NotImplementedError


class LangChainSearch(SearchOrchestrator):
    """LangChain retriever/LLM logic with deterministic summary fallback."""

    def __init__(self, store: StorageProtocol, embedder: EmbedderProtocol) -> None:
        self._store = store
        self._embedder = embedder

    def ask(
        self, handle: StorageHandle, query_text: str, settings: PipelineSettings
    ) -> SearchResult:
        start = time.perf_counter()
        query_embedding = self._embedder.embed_query(query_text, settings)
        ranked = self._store.query(query_embedding.vector, settings.top_k)
        sources = [self._to_source(embedding, score) for embedding, score in ranked]

        answer, fallback_used = self._invoke_langchain(
            handle, query_text, settings, default_answer=self._fallback_answer(query_text, sources)
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        confidence_scores = [score for _, score in ranked]
        logger.info(
            "Search completed",
            extra=safe_extra(
                {
                    "latency_ms": latency_ms,
                    "top_k": settings.top_k,
                    "fallback": fallback_used,
                    "question": query_text,
                }
            ),
        )
        return SearchResult(
            question=query_text,
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
            top_k=settings.top_k,
            confidence_scores=confidence_scores,
            fallback_used=fallback_used,
        )

    def _invoke_langchain(
        self,
        handle: StorageHandle,
        query_text: str,
        settings: PipelineSettings,
        *,
        default_answer: str,
    ) -> tuple[str, bool]:
        retriever = self._build_retriever(handle, settings)
        llm = self._build_llm()
        prompt_cls = PromptTemplate
        stuff_factory = create_stuff_documents_chain
        retrieval_factory = create_retrieval_chain
        if not retriever or not llm or not prompt_cls or not stuff_factory or not retrieval_factory:
            return default_answer, True
        assert (
            prompt_cls is not None and stuff_factory is not None and retrieval_factory is not None
        )
        try:  # pragma: no cover - heavy LangChain interaction
            prompt = prompt_cls.from_template(settings.prompt_template)
            docs_chain = stuff_factory(llm, prompt)
            qa_chain = retrieval_factory(retriever, docs_chain)
            response = qa_chain.invoke({"input": query_text})

            answer = (response.get("answer") or "").strip()
            return answer or default_answer, False
        except Exception as exc:
            logger.warning(
                "LangChain QA degraded; using fallback answer",
                extra=safe_extra({"error": str(exc)}),
            )
            return default_answer, True

    def _build_retriever(self, handle: StorageHandle, settings: PipelineSettings) -> Any | None:
        vectorstore = getattr(handle, "vectorstore", None)
        if vectorstore and hasattr(vectorstore, "as_retriever"):
            try:
                return vectorstore.as_retriever(search_kwargs={"k": settings.top_k})
            except Exception as exc:  # pragma: no cover - retriever optional
                logger.debug(
                    "Vectorstore retriever unavailable", extra=safe_extra({"error": str(exc)})
                )
                return None
        return None

    def _build_llm(self) -> Any | None:
        if HuggingFaceEndpoint is None:
            return None
        try:  # pragma: no cover - network dependent
            return HuggingFaceEndpoint(
                repo_id="mistralai/Mistral-7B-Instruct-v0.2",
                max_new_tokens=512,
                temperature=0.1,
                timeout=120,
            )
        except Exception as exc:
            logger.debug("HuggingFaceEndpoint unavailable", extra=safe_extra({"error": str(exc)}))
            return None

    def _fallback_answer(self, query_text: str, sources: list[RetrievedSource]) -> str:
        if not sources:
            raise SearchError(
                "Search returned no hits; try increasing TOP_K or verifying the loader output."
            )
        mean_confidence = statistics.mean(source.score for source in sources)
        snippets = ", ".join(source.text[:80].strip() for source in sources[:3])
        return (
            f"(degraded) Retrieved {len(sources)} chunks for '{query_text}'. "
            f"Mean confidence {mean_confidence:.2f}. Sources: {snippets}"
        )

    def _to_source(self, embedding: Any, score: float) -> RetrievedSource:
        metadata = dict(getattr(embedding, "metadata", {}))
        chunk_id = metadata.get("chunk_id") or getattr(embedding, "id", "chunk")
        text = (
            metadata.get("chunk_text") or metadata.get("snippet") or getattr(embedding, "text", "")
        )
        return RetrievedSource(chunk_id=chunk_id, score=score, text=text, metadata=metadata)
