"""Claude Code worker bridge — invokes Claude Code CLI with role-specific prompts.

Permission model:
  Each role gets minimal scoped permissions via --allowedTools.
  We use --permission-mode dontAsk so Claude never prompts interactively —
  any tool not in the allowlist is silently denied.
"""

from __future__ import annotations

import json
import subprocess
import os
from pathlib import Path
from typing import Any, Optional

from ..utils import get_package_root, iso_now


# ---------------------------------------------------------------------------
# Role definitions — each maps to a prompt file, state files, and permissions
# ---------------------------------------------------------------------------
#
# Claude Code's dontAsk mode + --allowedTools path globs are unreliable
# (absolute paths don't match, relative paths don't match).
# So we use UNSCOPED tool names (e.g. "Write", not "Write(path/**)")
# and rely on the role prompt to constrain which files Claude touches.
# The prompt explicitly lists "Files you MUST update" — that's the real
# access control. dontAsk just blocks tools not in the list at all
# (e.g. auditor has no Edit, so it can't edit source files).
# ---------------------------------------------------------------------------

# All roles can read
_READ_TOOLS = [
    "Read",
    "Glob",
    "Grep",
]

# Safe bash commands — no destructive operations
_BASH_SAFE = [
    "Bash(git diff *)",
    "Bash(git status *)",
    "Bash(git log *)",
    "Bash(python -m tianxing.*)",
    "Bash(python3 -m tianxing.*)",
    "Bash(ls *)",
    "Bash(cat *)",
    "Bash(head *)",
    "Bash(tail *)",
    "Bash(wc *)",
    "Bash(find *)",
]

ROLES = {
    "auditor": {
        "prompt_file": "prompts/revision_auditor.md",
        "reads": [
            "tianxing_revision/REVISION_SPEC.md",
            "tianxing_revision/CLAIMS_TO_PRESERVE.md",
            "tianxing_revision/OPERATOR_NOTES.md",
            "revision/state.json",
        ],
        "writes": [
            "revision/knowledge_state.json",
            "revision/claim_registry.json",
            "revision/observations.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",                # writes state files only (prompt-constrained)
            *_BASH_SAFE,
        ],
    },
    "planner": {
        "prompt_file": "prompts/revision_planner.md",
        "reads": [
            "tianxing_revision/REVISION_SPEC.md",
            "tianxing_revision/SUCCESS_CRITERIA.md",
            "tianxing_revision/EXPERIMENT_RULES.yaml",
            "tianxing_revision/OPERATOR_NOTES.md",
            "revision/state.json",
            "revision/knowledge_state.json",
            "revision/claim_registry.json",
        ],
        "writes": [
            "revision/master_plan.json",
            "revision/task_registry.json",
            "revision/decision_state.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",
            *_BASH_SAFE,
        ],
    },
    "implementer": {
        "prompt_file": "prompts/revision_implementer.md",
        "reads": [
            "tianxing_revision/REVISION_SPEC.md",
            "tianxing_revision/OPERATOR_NOTES.md",
            "revision/state.json",
            "revision/master_plan.json",
            "revision/task_registry.json",
            "revision/knowledge_state.json",
        ],
        "writes": [
            "revision/task_registry.json",
            "revision/result_registry.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",
            "Edit",                 # can edit paper + code (prompt-constrained)
            *_BASH_SAFE,
        ],
    },
    "verifier": {
        "prompt_file": "prompts/revision_verifier.md",
        "reads": [
            "tianxing_revision/CLAIMS_TO_PRESERVE.md",
            "revision/state.json",
            "revision/result_registry.json",
            "revision/claim_registry.json",
            "revision/knowledge_state.json",
        ],
        "writes": [
            "revision/claim_registry.json",
            "revision/observations.json",
            "revision/decision_state.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",
            *_BASH_SAFE,
        ],
    },
    "writeback": {
        "prompt_file": "prompts/revision_writeback.md",
        "reads": [
            "tianxing_revision/REVISION_SPEC.md",
            "revision/state.json",
            "revision/master_plan.json",
            "revision/claim_registry.json",
            "revision/result_registry.json",
            "revision/knowledge_state.json",
        ],
        "writes": [
            "revision/task_registry.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",
            "Edit",                 # can edit paper (prompt-constrained)
            *_BASH_SAFE,
        ],
    },
    "reflector": {
        "prompt_file": "prompts/revision_reflector.md",
        "reads": [
            "revision/state.json",
            "revision/result_registry.json",
            "revision/claim_registry.json",
            "revision/observations.json",
            "revision/knowledge_state.json",
            "revision/decision_state.json",
        ],
        "writes": [
            "revision/observations.json",
            "revision/decision_state.json",
            "revision/knowledge_state.json",
        ],
        "allowed_tools": [
            *_READ_TOOLS,
            "Write",
            *_BASH_SAFE,
        ],
    },
}


def build_task_prompt(
    role: str,
    project_root: str | Path,
    task_context: dict[str, Any] | None = None,
    extra_instructions: str = "",
) -> str:
    """Build the full prompt for a Claude Code invocation.

    Loads the role's prompt template, prepends context about which files to
    read and write, and appends any task-specific instructions.
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role}. Available: {list(ROLES.keys())}")

    role_def = ROLES[role]
    project_root = Path(project_root)
    pkg_root = get_package_root()

    # Load prompt template
    prompt_path = pkg_root / role_def["prompt_file"]
    if prompt_path.exists():
        role_prompt = prompt_path.read_text()
    else:
        role_prompt = f"You are the revision {role}. Follow standard procedures."

    # Build context header
    lines = [
        f"# Revision Task: {role.upper()}",
        f"",
        f"Project root: {project_root}",
        f"",
        f"## Files you MUST read before proceeding:",
        "",
    ]
    for f in role_def["reads"]:
        full = project_root / f
        lines.append(f"- `{full}`")

    lines.extend([
        "",
        "## Files you MUST update with your conclusions:",
        "",
    ])
    for f in role_def["writes"]:
        full = project_root / f
        lines.append(f"- `{full}`")

    lines.extend([
        "",
        "## CRITICAL RULE",
        "",
        "Do NOT rely on stdout for final business output.",
        "Persist ALL conclusions, decisions, and findings to the designated state files listed above.",
        "Your stdout should only contain brief progress notes.",
        "",
        "---",
        "",
    ])

    # Task-specific context
    if task_context:
        lines.extend([
            "## Task Context",
            "",
            "```json",
            json.dumps(task_context, ensure_ascii=False, indent=2),
            "```",
            "",
            "---",
            "",
        ])

    # Extra instructions (from MANUAL_OVERRIDES or operator)
    if extra_instructions:
        lines.extend([
            "## Additional Instructions",
            "",
            extra_instructions,
            "",
            "---",
            "",
        ])

    # Append role prompt
    lines.extend([
        "## Role Instructions",
        "",
        role_prompt,
    ])

    return "\n".join(lines)


def invoke_claude(
    role: str,
    project_root: str | Path,
    task_context: dict[str, Any] | None = None,
    extra_instructions: str = "",
    timeout: int = 600,
    model: str = "",
    max_turns: int = 30,
) -> dict[str, Any]:
    """Invoke Claude Code CLI with role-scoped permissions.

    Permission model:
      --permission-mode dontAsk    → never prompt; deny anything not in allowlist
      --allowedTools "Tool(scope)" → per-role minimal permissions

    Returns:
        {"ok": bool, "touched": [...], "stdout": str, "stderr": str}
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role}. Available: {list(ROLES.keys())}")

    project_root = Path(project_root).resolve()
    role_def = ROLES[role]
    prompt = build_task_prompt(role, project_root, task_context, extra_instructions)

    # Build command with scoped permissions
    cmd = [
        "claude",
        "-p", prompt,
        "--permission-mode", "dontAsk",
        "--output-format", "json",
        "--max-turns", str(max_turns),
    ]

    # Add per-role allowed tools (unscoped — prompt constrains actual targets)
    for tool in role_def["allowed_tools"]:
        cmd.extend(["--allowedTools", tool])

    if model:
        cmd.extend(["--model", model])

    try:
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Parse structured JSON output if possible
        stdout_text = result.stdout
        try:
            output = json.loads(stdout_text)
            # Claude Code JSON output has a "result" field with the response
            stdout_text = output.get("result", stdout_text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Check which state files were actually modified
        touched = []
        for f in role_def["writes"]:
            full = project_root / f
            if full.exists():
                touched.append(f)

        return {
            "ok": result.returncode == 0,
            "touched": touched,
            "stdout": stdout_text[-2000:] if len(stdout_text) > 2000 else stdout_text,
            "stderr": result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "touched": [],
            "stdout": "",
            "stderr": f"Claude Code timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "touched": [],
            "stdout": "",
            "stderr": "Claude Code CLI ('claude') not found. Is it installed?",
        }
