"""Atomic file operations for revision state files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..utils import iso_now


def atomic_write_json(path: str | Path, data: dict[str, Any]) -> None:
    """Write JSON atomically: tmp file + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=path.stem + "_"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def read_json(path: str | Path) -> dict[str, Any]:
    """Read a JSON file, returning empty dict if missing."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def update_json(path: str | Path, updates: dict[str, Any]) -> dict[str, Any]:
    """Read-modify-write a JSON file atomically."""
    data = read_json(path)
    data.update(updates)
    data["updated_at"] = iso_now()
    atomic_write_json(path, data)
    return data
