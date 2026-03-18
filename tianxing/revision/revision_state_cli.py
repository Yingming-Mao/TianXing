"""CLI for inspecting and managing revision state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..utils import get_project_root, json_result
from .claim_registry import ClaimRegistry
from .file_ops import read_json
from .result_registry import ResultRegistry
from .revision_state import RevisionState


def main():
    parser = argparse.ArgumentParser(description="Inspect or manage revision state")
    parser.add_argument(
        "--action",
        choices=["get", "confirm", "reset", "set-phase"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--root", type=str, default=None, help="Project root directory")
    parser.add_argument("--phase", type=str, default=None, help="Phase for set-phase action")
    args = parser.parse_args()

    root = Path(args.root) if args.root else get_project_root()
    revision_dir = root / "revision"

    if args.action == "get":
        state = RevisionState(revision_dir)
        plan = read_json(revision_dir / "master_plan.json")
        results = ResultRegistry(revision_dir)
        claims = ClaimRegistry(revision_dir)

        summary = {
            "phase": state.phase,
            "phase_status": state.phase_status,
            "subphase": state.subphase,
            "blocked": state.needs_human,
            "blocked_reason": state.blocked_reason,
            "current_task": state.current_task_id,
            "plan_tasks": len(plan.get("tasks", [])),
            "total_runs": len(results.runs),
            "running_experiments": len(results.list_by_status("running")),
            "completed_experiments": len(results.list_by_status("completed")),
            "total_claims": len(claims.claims),
            "verified_claims": len(claims.verified_claims()),
            "pending_claims": len(claims.pending_claims()),
            "contradicted_claims": len(claims.contradicted_claims()),
        }
        json_result(True, **summary)

    elif args.action == "confirm":
        state = RevisionState(revision_dir)
        if not state.needs_human:
            json_result(False, message="No pending human confirmation")
        state.clear_human_block()
        json_result(True, message="Human confirmation cleared", phase=state.phase)

    elif args.action == "reset":
        state = RevisionState(revision_dir)
        state.transition("INIT", "pending")
        json_result(True, message="State reset to INIT")

    elif args.action == "set-phase":
        if not args.phase:
            json_result(False, message="--phase is required for set-phase")
        state = RevisionState(revision_dir)
        state.transition(args.phase, "pending")
        json_result(True, message=f"Phase set to {args.phase}")


if __name__ == "__main__":
    main()
