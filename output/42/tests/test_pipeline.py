"""Smoke tests for the pyrag pipeline scaffolding."""

from __future__ import annotations

from pathlib import Path

from pyrag.config import PipelineSettings
from pyrag.pipeline import PipelineRunner


def test_pipeline_runner_emits_summary(tmp_path: Path) -> None:
    settings = PipelineSettings.from_env(
        {
            "DOC_CACHE_DIR": str(tmp_path),
        }
    )
    summary = PipelineRunner().run(settings)
    assert len(summary.documents) == 1
    assert len(summary.chunks) >= 1
    assert len(summary.embeddings) >= 1
    assert summary.search_result.answer
    assert summary.metrics["loader"]["count"] == 1
