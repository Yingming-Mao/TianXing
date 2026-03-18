"""Tests for RevisionState, ResultRegistry, and ClaimRegistry."""

import json
import pytest
from pathlib import Path

from tianxing.revision.revision_state import RevisionState
from tianxing.revision.result_registry import ResultRegistry
from tianxing.revision.claim_registry import ClaimRegistry
from tianxing.revision.revision_setup import setup


@pytest.fixture
def revision_dir(tmp_path):
    """Create a temporary revision directory with initial state."""
    setup(tmp_path)
    return tmp_path / "revision"


class TestRevisionState:
    def test_initial_state(self, revision_dir):
        state = RevisionState(revision_dir)
        assert state.phase == "INIT"
        assert state.phase_status == "pending"

    def test_transition(self, revision_dir):
        state = RevisionState(revision_dir)
        state.transition("AUDIT", "running")
        assert state.phase == "AUDIT"
        assert state.phase_status == "running"

    def test_transition_invalid_phase(self, revision_dir):
        state = RevisionState(revision_dir)
        with pytest.raises(ValueError):
            state.transition("BOGUS", "running")

    def test_advance(self, revision_dir):
        state = RevisionState(revision_dir)
        state.transition("AUDIT", "running")
        ok = state.advance()
        assert ok
        assert state.phase == "PLAN"

    def test_advance_at_end(self, revision_dir):
        state = RevisionState(revision_dir)
        state.transition("FINALIZE", "running")
        ok = state.advance()
        assert not ok
        assert state.phase_status == "completed"

    def test_human_block(self, revision_dir):
        state = RevisionState(revision_dir)
        state.request_human("Need approval for full run")
        assert state.needs_human
        assert state.phase_status == "blocked"
        state.clear_human_block()
        assert not state.needs_human
        assert state.phase_status == "running"

    def test_persistence(self, revision_dir):
        state = RevisionState(revision_dir)
        state.transition("PLAN", "running")
        # Reload from disk
        state2 = RevisionState(revision_dir)
        assert state2.phase == "PLAN"
        assert state2.phase_status == "running"

    def test_history_grows(self, revision_dir):
        state = RevisionState(revision_dir)
        state.transition("AUDIT", "running")
        state.transition("PLAN", "running")
        assert len(state.data["history"]) == 3  # INIT + AUDIT + PLAN


class TestResultRegistry:
    def test_add_and_get(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "Baseline experiment")
        run = reg.get_run("EXP-01")
        assert run is not None
        assert run["title"] == "Baseline experiment"
        assert run["runtime_status"] == "idle"

    def test_duplicate_run(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "First")
        with pytest.raises(ValueError):
            reg.add_run("EXP-01", "Duplicate")

    def test_status_transitions(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "Test")
        reg.set_runtime_status("EXP-01", "running")
        assert reg.get_run("EXP-01")["runtime_status"] == "running"
        assert reg.get_run("EXP-01")["started_at"] != ""
        reg.set_runtime_status("EXP-01", "completed")
        assert reg.get_run("EXP-01")["completed_at"] != ""

    def test_list_by_status(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "A")
        reg.add_run("EXP-02", "B")
        reg.set_runtime_status("EXP-01", "running")
        assert len(reg.list_by_status("running")) == 1
        assert len(reg.list_by_status("idle")) == 1

    def test_link_claim(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "Test")
        reg.link_claim("EXP-01", "C1")
        reg.link_claim("EXP-01", "C1")  # idempotent
        assert reg.get_run("EXP-01")["linked_claims"] == ["C1"]

    def test_persistence(self, revision_dir):
        reg = ResultRegistry(revision_dir)
        reg.add_run("EXP-01", "Test")
        reg2 = ResultRegistry(revision_dir)
        assert reg2.get_run("EXP-01") is not None


class TestClaimRegistry:
    def test_add_and_get(self, revision_dir):
        reg = ClaimRegistry(revision_dir)
        reg.add_claim("C1", "Our method is faster")
        claim = reg.get_claim("C1")
        assert claim["verdict"] == "pending"

    def test_set_verdict(self, revision_dir):
        reg = ClaimRegistry(revision_dir)
        reg.add_claim("C1", "Speed claim")
        reg.set_verdict("C1", "verified", "2x speedup measured")
        assert reg.get_claim("C1")["verdict"] == "verified"
        assert "2x" in reg.get_claim("C1")["evidence_summary"]

    def test_invalid_verdict(self, revision_dir):
        reg = ClaimRegistry(revision_dir)
        reg.add_claim("C1", "Test")
        with pytest.raises(ValueError):
            reg.set_verdict("C1", "bogus")

    def test_filters(self, revision_dir):
        reg = ClaimRegistry(revision_dir)
        reg.add_claim("C1", "Claim 1")
        reg.add_claim("C2", "Claim 2")
        reg.add_claim("C3", "Claim 3")
        reg.set_verdict("C1", "verified")
        reg.set_verdict("C2", "contradicted")
        assert len(reg.verified_claims()) == 1
        assert len(reg.contradicted_claims()) == 1
        assert len(reg.pending_claims()) == 1

    def test_link_run(self, revision_dir):
        reg = ClaimRegistry(revision_dir)
        reg.add_claim("C1", "Test")
        reg.link_run("C1", "EXP-01")
        assert "EXP-01" in reg.get_claim("C1")["dependent_runs"]
