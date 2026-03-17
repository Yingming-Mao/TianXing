"""Shared utility functions for paper-review-tools."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml


def load_config(path: Optional[str] = None) -> dict:
    """Load config.yaml, merging with defaults."""
    defaults = {
        "project": {"name": "paper", "paper_dir": "paper", "code_dir": "code", "results_dir": "results"},
        "compile": {"engine": "latexmk", "args": ["-pdf", "-interaction=nonstopmode"], "main_file": "paper/main.tex"},
        "tests": {"command": "pytest", "args": ["-x", "--tb=short"], "smoke_test_dir": "code/tests"},
        "review": {"max_rounds": 3, "target_score": 8.0, "stop_on_plateau": 2, "stop_on_fail": 2},
        "git": {"tag_prefix": "review-round-", "auto_checkpoint": True},
        "notification": {"method": "file"},
    }
    config_path = Path(path) if path else find_config()
    if config_path and config_path.exists():
        with open(config_path) as f:
            user_cfg = yaml.safe_load(f) or {}
        return _deep_merge(defaults, user_cfg)
    return defaults


def find_config() -> Optional[Path]:
    """Search for config.yaml from cwd upward."""
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        candidate = d / "config.yaml"
        if candidate.exists():
            return candidate
    return None


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def run_cmd(cmd: list[str], cwd: Optional[str] = None, timeout: int = 300) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def json_result(success: bool, **data: Any) -> None:
    """Print JSON result to stdout and exit."""
    result = {"ok": success, **data}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if success else 1)


def git_hash(cwd: Optional[str] = None) -> str:
    """Get current git commit hash."""
    code, out, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=cwd)
    return out.strip() if code == 0 else ""


def git_is_clean(cwd: Optional[str] = None) -> bool:
    """Check if git working tree is clean."""
    code, out, _ = run_cmd(["git", "status", "--porcelain"], cwd=cwd)
    return code == 0 and out.strip() == ""


def ensure_dirs(*paths: str) -> None:
    """Create directories if they don't exist."""
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def iso_now() -> str:
    """Return current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def get_project_root() -> Path:
    """Find project root by looking for config.yaml or .git."""
    cur = Path.cwd()
    for d in [cur, *cur.parents]:
        if (d / "config.yaml").exists() or (d / ".git").exists():
            return d
    return cur
