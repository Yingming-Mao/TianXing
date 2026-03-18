"""Result registry — tracks experiment runs and their outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..utils import iso_now
from .file_ops import atomic_write_json, read_json
from .schemas import (
    new_result_registry,
    new_run_entry,
    validate_runtime_status,
)


class ResultRegistry:
    """Manages result_registry.json."""

    def __init__(self, revision_dir: str | Path):
        self.path = Path(revision_dir) / "result_registry.json"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._data = read_json(self.path)
        if not self._data:
            self._data = new_result_registry()

    def save(self) -> None:
        self._data["updated_at"] = iso_now()
        atomic_write_json(self.path, self._data)

    def reload(self) -> None:
        self._load()

    @property
    def runs(self) -> list[dict[str, Any]]:
        return self._data.get("runs", [])

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        for r in self.runs:
            if r["run_id"] == run_id:
                return r
        return None

    def add_run(self, run_id: str, title: str, config_snapshot: dict | None = None) -> dict[str, Any]:
        if self.get_run(run_id):
            raise ValueError(f"Run already exists: {run_id}")
        entry = new_run_entry(run_id, title, config_snapshot)
        self._data["runs"].append(entry)
        self.save()
        return entry

    def update_run(self, run_id: str, **fields: Any) -> dict[str, Any]:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run not found: {run_id}")
        for k, v in fields.items():
            if k == "runtime_status" and not validate_runtime_status(v):
                raise ValueError(f"Invalid runtime_status: {v}")
            run[k] = v
        self.save()
        return run

    def set_runtime_status(self, run_id: str, status: str) -> None:
        now = iso_now()
        updates: dict[str, Any] = {"runtime_status": status}
        if status == "running":
            updates["started_at"] = now
        elif status in ("completed", "failed", "timed_out", "cancelled"):
            updates["completed_at"] = now
        self.update_run(run_id, **updates)

    def add_output(self, run_id: str, output_path: str, description: str = "") -> None:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run not found: {run_id}")
        run["outputs"].append({
            "path": output_path,
            "description": description,
            "recorded_at": iso_now(),
        })
        self.save()

    def link_claim(self, run_id: str, claim_id: str) -> None:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(f"Run not found: {run_id}")
        if claim_id not in run["linked_claims"]:
            run["linked_claims"].append(claim_id)
            self.save()

    def list_by_status(self, runtime_status: str) -> list[dict[str, Any]]:
        return [r for r in self.runs if r["runtime_status"] == runtime_status]
