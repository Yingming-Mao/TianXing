"""Initialize revision directory structure and template files."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ..utils import ensure_dirs, get_package_root, json_result
from .file_ops import atomic_write_json
from .schemas import (
    new_claim_registry,
    new_decision_state,
    new_knowledge_state,
    new_master_plan,
    new_observations,
    new_result_registry,
    new_state,
    new_task_registry,
)

# Template files that go into the user-input directory
INPUT_DIR = "tianxing_revision"
RUNTIME_DIR = "revision"

INPUT_TEMPLATES = {
    "REVISION_SPEC.md": """\
# Revision Specification

<!-- Describe the revision goals, reviewer comments to address, and new story arc. -->

## Reviewer Comments

<!-- Paste or summarize the reviewer/editor comments here. -->

## Revision Goals

<!-- What must change in the paper? What new experiments are needed? -->

## New Story Arc

<!-- If the paper's narrative is changing, describe the new story here. -->
""",
    "SUCCESS_CRITERIA.md": """\
# Success Criteria

<!-- Define what "done" looks like for this revision. -->

## Must-Have

- [ ] All reviewer comments addressed
- [ ] Paper compiles without errors
- [ ] All claims supported by experiments

## Nice-to-Have

- [ ] Score improvement on key dimensions
""",
    "EXPERIMENT_RULES.yaml": """\
# Experiment execution rules
smoke_first: true                # always run smoke test before full run
full_run_requires_confirmation: true  # human must confirm before full runs
max_concurrent_experiments: 2
max_experiment_runtime_hours: 24
retry_failed_experiments: true
max_retries: 2
""",
    "EXECUTION_ENV.yaml": """\
# Execution environment configuration
env: ""                          # conda env name, path, or venv python
gpu_required: false
gpu_count: 0
tmux_session_prefix: "tx-exp"
working_dir: ""                  # defaults to project root
proxy: ""                        # http proxy if needed
extra_env_vars: {}               # additional environment variables
""",
    "CLAIMS_TO_PRESERVE.md": """\
# Claims to Preserve

<!-- List the paper's key claims that must remain supported through the revision. -->
<!-- The system will track these and prevent writeback of text that contradicts them. -->

## Core Claims

1. <!-- Claim 1 description -->
2. <!-- Claim 2 description -->

## Secondary Claims

1. <!-- Claim description -->
""",
    "OPERATOR_NOTES.md": """\
# Operator Notes

<!-- Add any runtime notes, temporary instructions, or context here. -->
<!-- This file is read by Claude at the start of each invocation. -->
<!-- You can edit it at any time to steer the revision process. -->
""",
    "MANUAL_OVERRIDES.yaml": """\
# Manual overrides — edit at any time to steer the revision
# These take precedence over automatic decisions

skip_phases: []                  # e.g. ["SMOKE_TEST"] to skip smoke testing
force_rerun: []                  # run_ids to force re-execution
pause_after_phase: ""            # pause orchestrator after this phase completes
downgrade_claims: []             # claim_ids to mark as retired
extra_instructions: ""           # free-text instructions for Claude
""",
}


def setup(project_root: str | Path | None = None) -> dict:
    """Create revision directory structure and template files.

    Returns a dict with created paths for JSON output.
    """
    root = Path(project_root) if project_root else Path.cwd()
    input_dir = root / INPUT_DIR
    runtime_dir = root / RUNTIME_DIR

    # Create directories
    ensure_dirs(
        str(input_dir),
        str(runtime_dir),
        str(runtime_dir / "artifacts"),
        str(runtime_dir / "logs"),
        str(runtime_dir / "locks"),
        str(runtime_dir / "log_summaries"),
    )

    created_files = []

    # Write input templates (skip if already exists)
    for filename, content in INPUT_TEMPLATES.items():
        target = input_dir / filename
        if not target.exists():
            target.write_text(content)
            created_files.append(str(target))

    # Write runtime state files (skip if already exists)
    state_files = {
        "state.json": new_state,
        "knowledge_state.json": new_knowledge_state,
        "decision_state.json": new_decision_state,
        "master_plan.json": new_master_plan,
        "task_registry.json": new_task_registry,
        "result_registry.json": new_result_registry,
        "claim_registry.json": new_claim_registry,
        "observations.json": new_observations,
    }

    for filename, factory in state_files.items():
        target = runtime_dir / filename
        if not target.exists():
            atomic_write_json(target, factory())
            created_files.append(str(target))

    return {
        "input_dir": str(input_dir),
        "runtime_dir": str(runtime_dir),
        "created_files": created_files,
    }


def main():
    parser = argparse.ArgumentParser(description="Initialize revision directory structure")
    parser.add_argument("--root", type=str, default=None, help="Project root directory")
    args = parser.parse_args()

    result = setup(args.root)
    n = len(result["created_files"])
    json_result(True, message=f"Created {n} files", **result)


if __name__ == "__main__":
    main()
