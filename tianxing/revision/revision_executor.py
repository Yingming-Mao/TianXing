"""Revision executor — runs non-experiment tasks (invoke Claude roles, compile, test)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..utils import iso_now, load_config, run_cmd
from .claude_worker import invoke_claude
from .file_ops import read_json
from .revision_state import RevisionState


def load_overrides(project_root: Path) -> dict[str, Any]:
    """Load MANUAL_OVERRIDES.yaml if it exists."""
    p = project_root / "tianxing_revision" / "MANUAL_OVERRIDES.yaml"
    if p.exists():
        return yaml.safe_load(p.read_text()) or {}
    return {}


def load_operator_notes(project_root: Path) -> str:
    """Load OPERATOR_NOTES.md if it exists."""
    p = project_root / "tianxing_revision" / "OPERATOR_NOTES.md"
    if p.exists():
        return p.read_text()
    return ""


def invoke_role(
    role: str,
    project_root: Path,
    state: RevisionState,
    task_context: dict[str, Any] | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Invoke a Claude role with standard setup."""
    overrides = load_overrides(project_root)
    extra = overrides.get("extra_instructions", "")
    notes = load_operator_notes(project_root)
    if notes:
        extra = f"## Operator Notes\n\n{notes}\n\n{extra}"

    result = invoke_claude(
        role=role,
        project_root=project_root,
        task_context=task_context,
        extra_instructions=extra,
        timeout=timeout,
    )

    return result


def run_smoke_test(project_root: Path) -> dict[str, Any]:
    """Run compilation, syntax-check experiment scripts, and basic tests."""
    import glob as globmod

    project_root = Path(project_root)
    results: dict[str, Any] = {"compile": None, "experiment_syntax": None, "test": None}

    # 1. Compile paper
    code, stdout, stderr = run_cmd(
        ["python", "-m", "tianxing.compile_paper"],
        cwd=str(project_root),
        timeout=120,
    )
    results["compile"] = {"ok": code == 0, "stdout": stdout, "stderr": stderr}

    if code != 0:
        return {"ok": False, "results": results, "failed_at": "compile"}

    # 2. Syntax-check experiment scripts (import without executing)
    #    Find all run_experiment_*.py under the project
    exp_scripts = sorted(globmod.glob(
        str(project_root / "**" / "run_experiment_*.py"), recursive=True
    ))
    if exp_scripts:
        failed_scripts = []
        for script in exp_scripts:
            code, stdout, stderr = run_cmd(
                ["python", "-c", f"import ast; ast.parse(open('{script}').read())"],
                cwd=str(project_root),
                timeout=30,
            )
            if code != 0:
                failed_scripts.append({"script": script, "stderr": stderr})
        results["experiment_syntax"] = {
            "ok": len(failed_scripts) == 0,
            "checked": len(exp_scripts),
            "failed": failed_scripts,
        }
        if failed_scripts:
            return {"ok": False, "results": results, "failed_at": "experiment_syntax"}

    # 3. Tests (if enabled)
    config = load_config()
    if config.get("tests", {}).get("enabled", False):
        code, stdout, stderr = run_cmd(
            ["python", "-m", "tianxing.run_tests"],
            cwd=str(project_root),
            timeout=300,
        )
        results["test"] = {"ok": code == 0, "stdout": stdout, "stderr": stderr}
        if code != 0:
            return {"ok": False, "results": results, "failed_at": "test"}

    return {"ok": True, "results": results}
