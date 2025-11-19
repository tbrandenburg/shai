"""Integration tests for the uv-exposed pyrag CLI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI_CMD = ["uv", "run", "pyrag"]
DUMMY_PDF = ROOT / "tests" / "fixtures" / "dummy.pdf"


def _run_cli(extra_args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    assert DUMMY_PDF.is_file(), "Dummy PDF fixture missing"
    env = os.environ.copy()
    args = CLI_CMD + ["--pdf", str(DUMMY_PDF), "--query", "test"]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_cli_emits_answer_block() -> None:
    result = _run_cli()
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "Answer:" in output
    assert "Fallback used:" in output
    assert "Context:" in output


def test_cli_verbose_toggle() -> None:
    result = _run_cli(["--verbose"])
    assert result.returncode == 0, result.stderr
    assert "Fallback used:" in result.stdout
    assert "[INFO]" in result.stderr or "[WARNING]" in result.stderr
