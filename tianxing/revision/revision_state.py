"""Revision state machine — manages phase transitions and state persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from ..utils import iso_now
from .schemas import (
    PHASES,
    PHASE_STATUSES,
    new_state,
    validate_phase,
    validate_phase_status,
)


class RevisionState:
    """Manages the revision state file with atomic writes."""

    def __init__(self, revision_dir: str | Path):
        self.revision_dir = Path(revision_dir)
        self.state_file = self.revision_dir / "state.json"
        self._data: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.state_file.exists():
            self._data = json.loads(self.state_file.read_text())
        else:
            self._data = new_state()

    def save(self) -> None:
        """Atomic write: write to tmp file then rename."""
        self._data["updated_at"] = iso_now()
        self.revision_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.revision_dir), suffix=".tmp", prefix="state_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, str(self.state_file))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def reload(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def phase(self) -> str:
        return self._data.get("current_phase", "INIT")

    @property
    def phase_status(self) -> str:
        return self._data.get("phase_status", "pending")

    @property
    def subphase(self) -> str:
        return self._data.get("subphase", "")

    @property
    def blocked_reason(self) -> str:
        return self._data.get("blocked_reason", "")

    @property
    def needs_human(self) -> bool:
        return self._data.get("needs_human_confirmation", False)

    @property
    def current_task_id(self) -> str:
        return self._data.get("current_task_id", "")

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    # ------------------------------------------------------------------
    # Phase transitions
    # ------------------------------------------------------------------
    def transition(self, new_phase: str, status: str = "running") -> None:
        """Move to a new phase. Validates the transition is legal."""
        if not validate_phase(new_phase):
            raise ValueError(f"Invalid phase: {new_phase}")
        if not validate_phase_status(status):
            raise ValueError(f"Invalid status: {status}")

        now = iso_now()
        self._data["current_phase"] = new_phase
        self._data["phase_status"] = status
        self._data["subphase"] = ""
        self._data["blocked_reason"] = ""
        self._data["needs_human_confirmation"] = False
        self._data["history"].append({
            "phase": new_phase,
            "status": status,
            "timestamp": now,
        })
        self.save()

    def set_status(self, status: str, reason: str = "") -> None:
        """Update the status of the current phase."""
        if not validate_phase_status(status):
            raise ValueError(f"Invalid status: {status}")
        self._data["phase_status"] = status
        if reason:
            self._data["blocked_reason"] = reason
        self.save()

    def set_subphase(self, subphase: str) -> None:
        self._data["subphase"] = subphase
        self.save()

    def set_task(self, task_id: str) -> None:
        self._data["current_task_id"] = task_id
        self.save()

    def request_human(self, reason: str) -> None:
        self._data["needs_human_confirmation"] = True
        self._data["blocked_reason"] = reason
        self._data["phase_status"] = "blocked"
        self.save()

    def clear_human_block(self) -> None:
        self._data["needs_human_confirmation"] = False
        self._data["blocked_reason"] = ""
        self._data["phase_status"] = "running"
        self.save()

    def next_phase(self) -> Optional[str]:
        """Return the next phase in the sequence, or None if at the end."""
        try:
            idx = PHASES.index(self.phase)
            if idx + 1 < len(PHASES):
                return PHASES[idx + 1]
        except ValueError:
            pass
        return None

    def advance(self) -> bool:
        """Mark current phase completed and move to the next one.

        Returns True if advanced, False if already at the end.
        """
        nxt = self.next_phase()
        if nxt is None:
            self.set_status("completed")
            return False
        self.set_status("completed")
        self.transition(nxt, "running")
        return True
