"""Tests for revision schema factories and validation."""

import json
import pytest

from tianxing.revision.schemas import (
    PHASES,
    new_state,
    new_knowledge_state,
    new_decision_state,
    new_master_plan,
    new_task_registry,
    new_task_entry,
    new_result_registry,
    new_run_entry,
    new_claim_registry,
    new_claim_entry,
    new_observations,
    new_observation_entry,
    validate_phase,
    validate_phase_status,
    validate_runtime_status,
    validate_claim_verdict,
)


class TestFactories:
    """All factory functions produce valid, serializable JSON."""

    def test_new_state(self):
        s = new_state()
        assert s["current_phase"] == "INIT"
        assert s["phase_status"] == "pending"
        assert len(s["history"]) == 1
        json.dumps(s)  # must be serializable

    def test_new_knowledge_state(self):
        k = new_knowledge_state()
        assert k["key_claims"] == []
        json.dumps(k)

    def test_new_decision_state(self):
        d = new_decision_state()
        assert d["chosen_action"] == ""
        json.dumps(d)

    def test_new_master_plan(self):
        p = new_master_plan()
        assert p["tasks"] == []
        assert p["experiment_matrix"] == []
        json.dumps(p)

    def test_new_task_registry(self):
        t = new_task_registry()
        assert t["tasks"] == []
        json.dumps(t)

    def test_new_task_entry(self):
        e = new_task_entry("T1", "Fix intro", "paper")
        assert e["task_id"] == "T1"
        assert e["status"] == "pending"
        json.dumps(e)

    def test_new_result_registry(self):
        r = new_result_registry()
        assert r["runs"] == []
        json.dumps(r)

    def test_new_run_entry(self):
        e = new_run_entry("EXP-01", "Baseline", {"lr": 0.01})
        assert e["run_id"] == "EXP-01"
        assert e["runtime_status"] == "idle"
        assert e["config_snapshot"]["lr"] == 0.01
        json.dumps(e)

    def test_new_claim_registry(self):
        c = new_claim_registry()
        assert c["claims"] == []
        json.dumps(c)

    def test_new_claim_entry(self):
        e = new_claim_entry("C1", "Our method is faster")
        assert e["verdict"] == "pending"
        json.dumps(e)

    def test_new_observations(self):
        o = new_observations()
        assert o["entries"] == []
        json.dumps(o)

    def test_new_observation_entry(self):
        e = new_observation_entry("unexpected_result", "EXP-01", "Accuracy dropped")
        assert e["anomaly_type"] == "unexpected_result"
        json.dumps(e)


class TestValidation:
    def test_valid_phases(self):
        for p in PHASES:
            assert validate_phase(p)
        assert not validate_phase("NONEXISTENT")

    def test_valid_phase_statuses(self):
        assert validate_phase_status("running")
        assert not validate_phase_status("bogus")

    def test_valid_runtime_statuses(self):
        assert validate_runtime_status("completed")
        assert not validate_runtime_status("bogus")

    def test_valid_claim_verdicts(self):
        assert validate_claim_verdict("verified")
        assert validate_claim_verdict("contradicted")
        assert not validate_claim_verdict("bogus")
