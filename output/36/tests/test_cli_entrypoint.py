"""CLI-level integration tests executed through `uv run docling-milvus-rag`."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UV_EXECUTABLE = shutil.which("uv")


@pytest.mark.skipif(UV_EXECUTABLE is None, reason="uv CLI is required for this integration test")
def test_uv_cli_entrypoint_generates_report(tmp_path: Path) -> None:
    """The packaged Typer CLI should produce JSON artifacts and exit cleanly."""

    pdf_path = PROJECT_ROOT / "fixtures" / "dummy.pdf"
    if not pdf_path.exists():  # pragma: no cover - guard for CI caches
        pytest.skip("Dummy PDF is required for CLI integration tests.")

    report_path = tmp_path / "cli_report.json"
    milvus_path = tmp_path / "cli_test.db"
    question = "What content is inside the dummy PDF for CLI testing?"

    # Execute the CLI exactly how users will via `uv run docling-milvus-rag`.
    command = [
        UV_EXECUTABLE,
        "run",
        "docling-milvus-rag",
        "--pdf",
        str(pdf_path),
        "--question",
        question,
        "--output",
        str(report_path),
        "--milvus-uri",
        f"file:{milvus_path}",
        "--collection",
        "cli_test",
        "--llm-backend",
        "stub",
        "--log-level",
        "ERROR",
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=170,
    )

    failure_context = f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
    assert (
        completed.returncode == 0
    ), f"`uv run docling-milvus-rag` exited with {completed.returncode}. {failure_context}"
    assert report_path.exists(), f"CLI should emit JSON artifacts. {failure_context}"

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["question"] == question
    assert any(entry.endswith("dummy.pdf") for entry in payload["documents"])
    assert payload["chunks_indexed"] >= 1
    assert payload["answer"].strip(), f"Answer missing. {failure_context}"
    assert "Answer" in completed.stdout, f"Expected answer panel in stdout. {failure_context}"
