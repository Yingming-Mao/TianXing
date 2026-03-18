"""Claim registry — tracks paper claims and their verification status."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..utils import iso_now
from .file_ops import atomic_write_json, read_json
from .schemas import new_claim_entry, new_claim_registry, validate_claim_verdict


class ClaimRegistry:
    """Manages claim_registry.json."""

    def __init__(self, revision_dir: str | Path):
        self.path = Path(revision_dir) / "claim_registry.json"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        self._data = read_json(self.path)
        if not self._data:
            self._data = new_claim_registry()

    def save(self) -> None:
        self._data["updated_at"] = iso_now()
        atomic_write_json(self.path, self._data)

    def reload(self) -> None:
        self._load()

    @property
    def claims(self) -> list[dict[str, Any]]:
        return self._data.get("claims", [])

    def get_claim(self, claim_id: str) -> Optional[dict[str, Any]]:
        for c in self.claims:
            if c["claim_id"] == claim_id:
                return c
        return None

    def add_claim(self, claim_id: str, description: str) -> dict[str, Any]:
        if self.get_claim(claim_id):
            raise ValueError(f"Claim already exists: {claim_id}")
        entry = new_claim_entry(claim_id, description)
        self._data["claims"].append(entry)
        self.save()
        return entry

    def set_verdict(self, claim_id: str, verdict: str, evidence: str = "") -> None:
        if not validate_claim_verdict(verdict):
            raise ValueError(f"Invalid verdict: {verdict}")
        claim = self.get_claim(claim_id)
        if not claim:
            raise KeyError(f"Claim not found: {claim_id}")
        claim["verdict"] = verdict
        if evidence:
            claim["evidence_summary"] = evidence
        claim["updated_at"] = iso_now()
        self.save()

    def add_paper_location(self, claim_id: str, location: str) -> None:
        claim = self.get_claim(claim_id)
        if not claim:
            raise KeyError(f"Claim not found: {claim_id}")
        if location not in claim["paper_locations"]:
            claim["paper_locations"].append(location)
            self.save()

    def link_run(self, claim_id: str, run_id: str) -> None:
        claim = self.get_claim(claim_id)
        if not claim:
            raise KeyError(f"Claim not found: {claim_id}")
        if run_id not in claim["dependent_runs"]:
            claim["dependent_runs"].append(run_id)
            self.save()

    def verified_claims(self) -> list[dict[str, Any]]:
        return [c for c in self.claims if c["verdict"] == "verified"]

    def pending_claims(self) -> list[dict[str, Any]]:
        return [c for c in self.claims if c["verdict"] == "pending"]

    def contradicted_claims(self) -> list[dict[str, Any]]:
        return [c for c in self.claims if c["verdict"] == "contradicted"]
