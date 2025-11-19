"""Simple file-backed cache utilities used across the pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class Cache:
    """Filesystem-backed cache for deterministic offline runs."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def read(self, key: str) -> Any | None:
        path = self._key_path(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def write(self, key: str, value: Any) -> None:
        path = self._key_path(key)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(value, fp, ensure_ascii=False, indent=2)


class NoOpCache(Cache):
    """Cache implementation that simply never persists values."""

    def __init__(self) -> None:  # pragma: no cover - trivial
        self.root = Path("/dev/null")

    def read(self, key: str) -> Any | None:  # noqa: D401 - simple override
        return None

    def write(self, key: str, value: Any) -> None:  # noqa: D401 - simple override
        return None
