"""Smoke tests for the pyrag pipeline scaffolding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyrag.config import PipelineSettings
from pyrag.embedder import MiniLMEmbedder
from pyrag.pipeline import PipelineRunner


def _force_hash_embeddings(monkeypatch: Any) -> None:
    def _disable_model(self: MiniLMEmbedder, settings: PipelineSettings):  # type: ignore[override]
        return None

    monkeypatch.setattr(MiniLMEmbedder, "_ensure_model", _disable_model, raising=False)


def test_pipeline_runner_emits_summary(tmp_path: Path, monkeypatch: Any) -> None:
    _force_hash_embeddings(monkeypatch)
    settings = PipelineSettings.from_env(
        {
            "DOC_CACHE_DIR": str(tmp_path),
        }
    )
    summary = PipelineRunner().run(settings)
    assert len(summary.documents) >= 1
    assert len(summary.chunks) >= 1
    assert len(summary.embeddings) >= 1
    assert summary.search_result.answer
    assert summary.metrics["loader"]["count"] >= 1
