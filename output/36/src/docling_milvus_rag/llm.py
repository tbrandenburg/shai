"""Answer generation via llama.cpp with deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:  # pragma: no cover - optional dependency
    from llama_cpp import Llama
except Exception:  # pragma: no cover - fallback path
    Llama = None  # type: ignore[assignment]

from .config import LLMConfig
from .milvus_store import RetrievedChunk


@dataclass
class AnswerResult:
    answer: str
    citations: list[str]
    metrics: dict[str, float]


class AnswerGenerator:
    """Wrap llama.cpp while keeping a graceful offline fallback."""

    def __init__(self, cfg: LLMConfig) -> None:
        self.cfg = cfg
        self._llm = None
        if cfg.model_path and Llama is not None:
            model_path = Path(cfg.model_path)
            if not model_path.exists():
                raise FileNotFoundError(
                    f"LLM weights not found at {model_path}. Provide a GGUF file or disable generation."
                )
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=cfg.context_window,
                n_threads=4,
            )

    def generate(self, question: str, contexts: Iterable[RetrievedChunk]) -> AnswerResult:
        context_list = list(contexts)
        context_text = "\n".join(chunk.text for chunk in context_list)
        citations = [chunk.metadata.get("source", "unknown") for chunk in context_list]
        if self._llm is None:
            answer = self._fallback_answer(question, context_text)
            return AnswerResult(answer=answer, citations=citations, metrics={})
        prompt = self._build_prompt(question, context_text)
        response = self._llm(
            prompt,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
        )
        text = response["choices"][0]["text"].strip()
        metrics = {"tokens": float(response.get("usage", {}).get("total_tokens", 0))}
        return AnswerResult(answer=text, citations=citations, metrics=metrics)

    def _build_prompt(self, question: str, context_text: str) -> str:
        return (
            "You are an offline assistant that only uses the provided context.\n"
            "Context:\n"
            f"{context_text}\n"
            "Answer the question concisely and cite document sources."
            f"\nQuestion: {question}\nAnswer:"
        )

    def _fallback_answer(self, question: str, context_text: str) -> str:
        if not context_text.strip():
            return "No context available to answer the question."
        summary = context_text.split("\n")[0][:280]
        return f"Offline fallback answer for '{question}': {summary}"
