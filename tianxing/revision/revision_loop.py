"""Main orchestration loop — the Python governor that drives the revision process.

This is the core event loop described in the architecture:
1. Read all state files
2. Check current phase
3. Determine next action
4. Execute action (invoke Claude or run experiment)
5. Update state
6. Sleep or continue
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from ..utils import ensure_dirs, get_project_root, iso_now, json_result, load_config
from .claim_registry import ClaimRegistry
from .experiment_runner import ExperimentRunner
from .file_ops import read_json
from .result_registry import ResultRegistry
from .revision_executor import invoke_role, load_overrides, run_smoke_test
from .revision_state import RevisionState


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------
ACTIONS = [
    "invoke_auditor",
    "invoke_planner",
    "invoke_implementer",
    "run_smoke_tests",
    "run_full_experiment",
    "validate_experiment_outputs",
    "invoke_verifier",
    "invoke_writeback_draft",
    "invoke_writeback_final",
    "invoke_reflector",
    "request_human_confirmation",
    "finalize",
    "wait",
]


class RevisionLoop:
    """The main orchestration loop."""

    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root) if project_root else get_project_root()
        self.revision_dir = self.project_root / "revision"
        self.input_dir = self.project_root / "tianxing_revision"

        # Core state objects
        self.state = RevisionState(self.revision_dir)
        self.results = ResultRegistry(self.revision_dir)
        self.claims = ClaimRegistry(self.revision_dir)
        self.runner = ExperimentRunner(self.project_root, self.revision_dir)
        self.config = load_config()

    def reload_all(self) -> None:
        """Reload all state from disk."""
        self.state.reload()
        self.results.reload()
        self.claims.reload()

    def load_overrides(self) -> dict[str, Any]:
        return load_overrides(self.project_root)

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------
    def determine_action(self) -> str:
        """Determine the next action based on current state."""
        phase = self.state.phase
        status = self.state.phase_status
        overrides = self.load_overrides()

        # Check for skip overrides
        skip = overrides.get("skip_phases", [])
        if phase in skip:
            return "skip"

        # Check for pause
        pause_after = overrides.get("pause_after_phase", "")

        # Blocked — need human
        if self.state.needs_human:
            return "request_human_confirmation"

        # Phase-to-action mapping
        if phase == "INIT" and status in ("pending", "running"):
            return "invoke_auditor"

        if phase == "AUDIT":
            if status == "running":
                return "wait"
            if status == "completed":
                return "invoke_planner"
            if status == "failed":
                return "invoke_auditor"  # retry

        if phase == "PLAN":
            if status == "running":
                return "wait"
            if status == "completed":
                return "invoke_implementer"
            if status == "failed":
                return "invoke_planner"

        if phase == "IMPLEMENT":
            if status == "running":
                return "wait"
            if status == "completed":
                return "run_smoke_tests"
            if status == "failed":
                return "invoke_reflector"

        if phase == "SMOKE_TEST":
            if status == "running":
                return "wait"
            if status == "completed":
                # Check if full runs are needed
                plan = read_json(self.revision_dir / "master_plan.json")
                if plan.get("experiment_matrix"):
                    return "request_human_confirmation"
                return "invoke_verifier"
            if status == "failed":
                return "invoke_reflector"

        if phase == "FULL_RUN":
            if status == "running":
                return "validate_experiment_outputs"
            if status == "completed":
                return "invoke_verifier"
            if status == "failed":
                return "invoke_reflector"

        if phase == "VERIFY":
            if status == "running":
                return "wait"
            if status == "completed":
                return "invoke_writeback_draft"
            if status == "failed":
                return "invoke_reflector"

        if phase == "WRITEBACK_DRAFT":
            if status == "running":
                return "wait"
            if status == "completed":
                return "invoke_writeback_final"

        if phase == "WRITEBACK_FINAL":
            if status == "running":
                return "wait"
            if status == "completed":
                return "finalize"

        if phase == "FINALIZE":
            return "finalize"

        return "wait"

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------
    def execute_action(self, action: str) -> dict[str, Any]:
        """Execute a single action and return the result."""
        log = {"action": action, "timestamp": iso_now()}

        if action == "invoke_auditor":
            self.state.transition("AUDIT", "running")
            result = invoke_role("auditor", self.project_root, self.state, timeout=600)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "invoke_planner":
            self.state.transition("PLAN", "running")
            result = invoke_role("planner", self.project_root, self.state, timeout=600)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "invoke_implementer":
            self.state.transition("IMPLEMENT", "running")
            # Pass current task from plan
            plan = read_json(self.revision_dir / "master_plan.json")
            task_ctx = {"tasks": plan.get("tasks", [])}
            result = invoke_role("implementer", self.project_root, self.state,
                                 task_context=task_ctx, timeout=900)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "run_smoke_tests":
            self.state.transition("SMOKE_TEST", "running")
            result = run_smoke_test(self.project_root)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("failed_at", "unknown"))
            log["result"] = result

        elif action == "invoke_verifier":
            self.state.transition("VERIFY", "running")
            result = invoke_role("verifier", self.project_root, self.state, timeout=600)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "invoke_writeback_draft":
            self.state.transition("WRITEBACK_DRAFT", "running")
            result = invoke_role("writeback", self.project_root, self.state,
                                 task_context={"mode": "draft"}, timeout=600)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "invoke_writeback_final":
            self.state.transition("WRITEBACK_FINAL", "running")
            # Only proceed if we have verified claims
            verified = self.claims.verified_claims()
            result = invoke_role("writeback", self.project_root, self.state,
                                 task_context={"mode": "final", "verified_claims": len(verified)},
                                 timeout=600)
            if result["ok"]:
                self.state.set_status("completed")
            else:
                self.state.set_status("failed", result.get("stderr", ""))
            log["result"] = result

        elif action == "invoke_reflector":
            result = invoke_role("reflector", self.project_root, self.state, timeout=300)
            # Reflector may recommend replan — check decision_state
            decision = read_json(self.revision_dir / "decision_state.json")
            if decision.get("chosen_action") == "replan":
                self.state.transition("PLAN", "pending")
            log["result"] = result

        elif action == "request_human_confirmation":
            self.state.request_human("Full experiment run requires confirmation")
            log["result"] = {"waiting": True}

        elif action == "finalize":
            self.state.transition("FINALIZE", "completed")
            log["result"] = {"finalized": True}

        elif action == "validate_experiment_outputs":
            # Check running experiments
            running = self.results.list_by_status("running")
            all_done = True
            for run in running:
                check = self.runner.check_running(run["run_id"])
                if not check["running"]:
                    # Generate summary and update status
                    self.runner.generate_log_summary(run["run_id"])
                    self.results.set_runtime_status(run["run_id"], "completed")
                else:
                    all_done = False
            if all_done and not running:
                self.state.set_status("completed")
            log["result"] = {"all_done": all_done, "running_count": len(running)}

        elif action == "skip":
            self.state.advance()
            log["result"] = {"skipped": True}

        elif action == "wait":
            log["result"] = {"waiting": True}

        return log

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run_once(self) -> dict[str, Any]:
        """Run a single iteration of the loop."""
        self.reload_all()
        action = self.determine_action()
        result = self.execute_action(action)
        return result

    def run(self, max_iterations: int = 50, poll_interval: float = 5.0) -> None:
        """Run the full orchestration loop until completion or max iterations."""
        print(f"[revise] Starting revision loop at {self.project_root}")
        print(f"[revise] Current phase: {self.state.phase} ({self.state.phase_status})")

        for i in range(max_iterations):
            self.reload_all()

            # Check termination
            if self.state.phase == "FINALIZE" and self.state.phase_status == "completed":
                print("[revise] Revision complete.")
                return

            # Check if blocked
            if self.state.needs_human:
                print(f"[revise] Blocked: {self.state.blocked_reason}")
                print("[revise] Run 'tianxing revise-state --action confirm' to continue.")
                return

            action = self.determine_action()
            if action == "wait":
                print(f"[revise] Waiting... (phase={self.state.phase}, status={self.state.phase_status})")
                time.sleep(poll_interval)
                continue

            print(f"[revise] [{i+1}/{max_iterations}] Action: {action}")
            result = self.execute_action(action)

            ok = result.get("result", {}).get("ok", True)
            if not ok:
                err = result.get("result", {}).get("stderr", "")
                print(f"[revise] Action failed: {err[:200]}")

        print(f"[revise] Reached max iterations ({max_iterations})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run the revision orchestration loop")
    parser.add_argument("--root", type=str, default=None, help="Project root directory")
    parser.add_argument("--once", action="store_true", help="Run a single iteration")
    parser.add_argument("--max-iter", type=int, default=50, help="Max loop iterations")
    parser.add_argument("--poll", type=float, default=5.0, help="Poll interval (seconds)")
    args = parser.parse_args()

    loop = RevisionLoop(args.root)

    if args.once:
        result = loop.run_once()
        json_result(True, **result)
    else:
        loop.run(max_iterations=args.max_iter, poll_interval=args.poll)


if __name__ == "__main__":
    main()
