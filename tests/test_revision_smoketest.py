"""End-to-end smoke test: setup → AUDIT → PLAN → IMPLEMENT → SMOKE_TEST.

Mocks the Claude Code CLI so the full orchestration loop can run without
actually invoking Claude. Validates that:
- State transitions happen correctly
- Registries get populated
- The loop terminates at the right point
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tianxing.revision.revision_setup import setup
from tianxing.revision.revision_state import RevisionState
from tianxing.revision.revision_loop import RevisionLoop
from tianxing.revision.result_registry import ResultRegistry
from tianxing.revision.claim_registry import ClaimRegistry
from tianxing.revision.file_ops import atomic_write_json, read_json


# ---------------------------------------------------------------------------
# Helpers: simulate what Claude would write to state files
# ---------------------------------------------------------------------------

def fake_auditor(project_root: Path):
    """Simulate the auditor role: populate knowledge_state + claim_registry."""
    rd = project_root / "revision"

    # knowledge_state
    atomic_write_json(rd / "knowledge_state.json", {
        "schema_version": "0.1.0",
        "current_paper_story": "This paper proposes a service-envelope method for EV charging.",
        "key_claims": [
            {"id": "C1", "text": "Service envelope reduces cost by 15%", "strength": "moderate", "evidence": "Table 1"},
            {"id": "C2", "text": "Method scales to 1000 EVs", "strength": "weak", "evidence": "Section 4.3"},
        ],
        "assumptions": ["Charging demand follows Poisson process"],
        "risks": [{"risk": "Scalability claim C2 has thin evidence", "severity": "high", "mitigation": "Run large-scale experiment"}],
        "anomalies": [],
        "open_questions": ["What is the baseline comparison?"],
        "paper_code_alignment": "Code matches paper for small-scale. Large-scale experiment code exists but results not in paper.",
        "updated_at": "2026-03-18T00:00:00Z",
    })

    # claim_registry
    atomic_write_json(rd / "claim_registry.json", {
        "schema_version": "0.1.0",
        "claims": [
            {"claim_id": "C1", "description": "Service envelope reduces cost by 15%",
             "paper_locations": ["Abstract", "Section 3.2", "Table 1"],
             "dependent_runs": [], "verdict": "pending", "evidence_summary": "", "updated_at": "2026-03-18T00:00:00Z"},
            {"claim_id": "C2", "description": "Method scales to 1000 EVs",
             "paper_locations": ["Section 4.3"],
             "dependent_runs": [], "verdict": "pending", "evidence_summary": "", "updated_at": "2026-03-18T00:00:00Z"},
        ],
        "updated_at": "2026-03-18T00:00:00Z",
    })


def fake_planner(project_root: Path):
    """Simulate the planner role: populate master_plan + task_registry."""
    rd = project_root / "revision"

    atomic_write_json(rd / "master_plan.json", {
        "schema_version": "0.1.0",
        "story_arc": "Reframe around service-envelope as a scalable, cost-effective EV charging strategy.",
        "sections_to_update": [
            {"section": "Abstract", "action": "rewrite", "reason": "Emphasize scalability"},
            {"section": "Section 4.3", "action": "update", "reason": "Add large-scale results"},
        ],
        "tasks": [
            {"task_id": "T1", "title": "Rewrite abstract", "type": "paper", "depends_on": [], "priority": "high",
             "description": "Update abstract to emphasize scalability and new results"},
            {"task_id": "T2", "title": "Update training script for 1000 EVs", "type": "code", "depends_on": [], "priority": "high",
             "description": "Modify run_experiment.py to support 1000-EV scenario"},
            {"task_id": "T3", "title": "Run large-scale experiment", "type": "experiment", "depends_on": ["T2"], "priority": "high",
             "description": "Execute 1000-EV simulation"},
        ],
        "experiment_matrix": [
            {"run_id": "EXP-SCALE", "title": "1000-EV scalability test",
             "smoke_command": "python code/run_experiment.py --evs 10 --epochs 1",
             "full_command": "python code/run_experiment.py --evs 1000 --epochs 100",
             "expected_outputs": ["results/scale_1000.csv"],
             "success_criteria": "Cost reduction >= 10%",
             "linked_claims": ["C2"], "estimated_runtime": "4h"},
        ],
        "dependencies": [{"from": "T2", "to": "T3", "type": "blocks"}],
        "updated_at": "2026-03-18T00:00:00Z",
    })

    atomic_write_json(rd / "task_registry.json", {
        "schema_version": "0.1.0",
        "tasks": [
            {"task_id": "T1", "title": "Rewrite abstract", "type": "paper", "status": "pending",
             "created_at": "2026-03-18T00:00:00Z", "started_at": "", "completed_at": "", "notes": "", "artifacts": []},
            {"task_id": "T2", "title": "Update training script", "type": "code", "status": "pending",
             "created_at": "2026-03-18T00:00:00Z", "started_at": "", "completed_at": "", "notes": "", "artifacts": []},
            {"task_id": "T3", "title": "Run large-scale experiment", "type": "experiment", "status": "pending",
             "created_at": "2026-03-18T00:00:00Z", "started_at": "", "completed_at": "", "notes": "", "artifacts": []},
        ],
        "updated_at": "2026-03-18T00:00:00Z",
    })

    atomic_write_json(rd / "decision_state.json", {
        "schema_version": "0.1.0",
        "next_candidate_actions": [],
        "chosen_action": "proceed_to_implementation",
        "rejected_actions": ["skip_scalability_experiment"],
        "why_chosen": "Scalability claim C2 needs stronger evidence",
        "escalation_needed": False,
        "updated_at": "2026-03-18T00:00:00Z",
    })


def fake_implementer(project_root: Path):
    """Simulate the implementer: mark tasks done, register experiment."""
    rd = project_root / "revision"

    # Update task registry — mark T1 and T2 completed
    tasks = read_json(rd / "task_registry.json")
    for t in tasks["tasks"]:
        if t["task_id"] in ("T1", "T2"):
            t["status"] = "completed"
            t["completed_at"] = "2026-03-18T00:01:00Z"
    atomic_write_json(rd / "task_registry.json", tasks)

    # Register experiment in result registry
    atomic_write_json(rd / "result_registry.json", {
        "schema_version": "0.1.0",
        "runs": [{
            "run_id": "EXP-SCALE",
            "title": "1000-EV scalability test",
            "runtime_status": "idle",
            "semantic_status": "",
            "config_snapshot": {"evs": 1000, "epochs": 100},
            "logs": [], "checkpoints": [], "outputs": [],
            "linked_claims": ["C2"],
            "created_at": "2026-03-18T00:01:00Z",
            "started_at": "", "completed_at": "",
        }],
        "updated_at": "2026-03-18T00:01:00Z",
    })

    # Simulate actual file changes (create a dummy modified abstract)
    paper_dir = project_root / "paper"
    paper_dir.mkdir(exist_ok=True)
    (paper_dir / "main.tex").write_text(
        "\\begin{abstract}\nRevised: Service-envelope method reduces cost by 15\\% "
        "and scales to 1000 EVs.\n\\end{abstract}\n"
    )


def mock_invoke_claude(role, project_root, state, task_context=None, timeout=600):
    """Mock Claude invocation — call the appropriate fake function."""
    project_root = Path(project_root)

    simulators = {
        "auditor": fake_auditor,
        "planner": fake_planner,
        "implementer": fake_implementer,
    }

    if role in simulators:
        simulators[role](project_root)

    return {"ok": True, "touched": [], "stdout": f"[mock {role}] done", "stderr": ""}


def mock_smoke_test(project_root):
    """Mock smoke test — always passes."""
    return {"ok": True, "results": {"compile": {"ok": True}, "test": None}}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """Create a minimal paper project with revision scaffolding."""
    # Minimal paper
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\begin{abstract}Original abstract.\\end{abstract}\n"
        "\\section{Introduction}Hello world.\n"
        "\\end{document}\n"
    )

    # Minimal code
    code_dir = tmp_path / "code"
    code_dir.mkdir()
    (code_dir / "run_experiment.py").write_text("print('running experiment')\n")

    # Config
    (tmp_path / "config.yaml").write_text(
        "project:\n  name: smoke-test\n  paper_dir: paper\n  code_dir: code\n"
    )

    # Git init (needed for get_project_root)
    os.system(f"cd {tmp_path} && git init -q && git add -A && git commit -q -m init")

    # Setup revision scaffolding
    setup(tmp_path)

    # Fill in revision spec so it's not empty
    (tmp_path / "tianxing_revision" / "REVISION_SPEC.md").write_text(
        "# Revision Spec\n\n## Goals\n- Strengthen scalability claim\n- Add 1000-EV experiment\n"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSmokeE2E:
    """Walk through INIT → AUDIT → PLAN → IMPLEMENT → SMOKE_TEST."""

    @patch("tianxing.revision.revision_loop.invoke_role", side_effect=mock_invoke_claude)
    @patch("tianxing.revision.revision_loop.run_smoke_test", side_effect=mock_smoke_test)
    def test_full_flow(self, mock_smoke, mock_claude, project):
        loop = RevisionLoop(project)

        # --- Step 1: INIT → AUDIT ---
        assert loop.state.phase == "INIT"
        result = loop.run_once()
        assert result["action"] == "invoke_auditor"
        loop.reload_all()
        assert loop.state.phase == "AUDIT"
        assert loop.state.phase_status == "completed"

        # Verify auditor populated knowledge state
        ks = read_json(project / "revision" / "knowledge_state.json")
        assert "service-envelope" in ks["current_paper_story"]
        assert len(ks["key_claims"]) == 2

        # Verify claims registered
        assert len(loop.claims.claims) == 2
        assert loop.claims.get_claim("C1")["verdict"] == "pending"

        # --- Step 2: AUDIT completed → PLAN ---
        result = loop.run_once()
        assert result["action"] == "invoke_planner"
        loop.reload_all()
        assert loop.state.phase == "PLAN"
        assert loop.state.phase_status == "completed"

        # Verify plan created
        plan = read_json(project / "revision" / "master_plan.json")
        assert len(plan["tasks"]) == 3
        assert len(plan["experiment_matrix"]) == 1
        assert plan["experiment_matrix"][0]["run_id"] == "EXP-SCALE"

        # --- Step 3: PLAN completed → IMPLEMENT ---
        result = loop.run_once()
        assert result["action"] == "invoke_implementer"
        loop.reload_all()
        assert loop.state.phase == "IMPLEMENT"
        assert loop.state.phase_status == "completed"

        # Verify tasks updated
        tasks = read_json(project / "revision" / "task_registry.json")
        completed = [t for t in tasks["tasks"] if t["status"] == "completed"]
        assert len(completed) == 2  # T1, T2

        # Verify experiment registered
        assert loop.results.get_run("EXP-SCALE") is not None

        # Verify paper was modified
        paper = (project / "paper" / "main.tex").read_text()
        assert "Revised" in paper

        # --- Step 4: IMPLEMENT completed → SMOKE_TEST ---
        result = loop.run_once()
        assert result["action"] == "run_smoke_tests"
        loop.reload_all()
        assert loop.state.phase == "SMOKE_TEST"
        assert loop.state.phase_status == "completed"

        # --- Step 5: SMOKE_TEST completed, experiment matrix exists → HUMAN CONFIRMATION ---
        result = loop.run_once()
        assert result["action"] == "request_human_confirmation"
        loop.reload_all()
        assert loop.state.needs_human
        assert "Full experiment" in loop.state.blocked_reason

    @patch("tianxing.revision.revision_loop.invoke_role", side_effect=mock_invoke_claude)
    @patch("tianxing.revision.revision_loop.run_smoke_test", side_effect=mock_smoke_test)
    def test_human_confirm_and_resume(self, mock_smoke, mock_claude, project):
        """After human confirms, loop should resume."""
        loop = RevisionLoop(project)

        # Run until blocked
        for _ in range(5):
            loop.run_once()
            loop.reload_all()
            if loop.state.needs_human:
                break

        assert loop.state.needs_human

        # Simulate human confirmation
        loop.state.clear_human_block()
        assert not loop.state.needs_human
        assert loop.state.phase_status == "running"

    @patch("tianxing.revision.revision_loop.invoke_role", side_effect=mock_invoke_claude)
    @patch("tianxing.revision.revision_loop.run_smoke_test", side_effect=mock_smoke_test)
    def test_state_history_accumulates(self, mock_smoke, mock_claude, project):
        """State history should record all phase transitions."""
        loop = RevisionLoop(project)

        for _ in range(4):
            loop.run_once()
            loop.reload_all()

        history = loop.state.data["history"]
        phases_seen = [h["phase"] for h in history]
        assert "INIT" in phases_seen
        assert "AUDIT" in phases_seen
        assert "PLAN" in phases_seen
        assert "IMPLEMENT" in phases_seen


class TestSetupCLI:
    """Test the setup produces a usable project."""

    def test_setup_then_state(self, project):
        state = RevisionState(project / "revision")
        assert state.phase == "INIT"

        results = ResultRegistry(project / "revision")
        assert len(results.runs) == 0

        claims = ClaimRegistry(project / "revision")
        assert len(claims.claims) == 0

    def test_all_state_files_valid_json(self, project):
        rd = project / "revision"
        for name in [
            "state.json", "knowledge_state.json", "decision_state.json",
            "master_plan.json", "task_registry.json", "result_registry.json",
            "claim_registry.json", "observations.json",
        ]:
            data = json.loads((rd / name).read_text())
            assert "schema_version" in data, f"{name} missing schema_version"
