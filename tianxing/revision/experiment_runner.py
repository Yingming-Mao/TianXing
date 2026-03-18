"""Experiment runner — manages background experiment execution.

Phase 2 implementation. This module provides the skeleton for:
- Starting background experiments (subprocess / tmux)
- Monitoring heartbeats and timeouts
- Generating log summaries for Claude
- Updating the result registry
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Optional

import yaml

from ..utils import ensure_dirs, iso_now, run_cmd
from .file_ops import atomic_write_json, read_json
from .result_registry import ResultRegistry


class ExperimentRunner:
    """Manages background experiment execution."""

    def __init__(self, project_root: str | Path, revision_dir: str | Path):
        self.project_root = Path(project_root)
        self.revision_dir = Path(revision_dir)
        self.registry = ResultRegistry(self.revision_dir)
        self.log_dir = self.revision_dir / "logs"
        self.summary_dir = self.revision_dir / "log_summaries"
        ensure_dirs(str(self.log_dir), str(self.summary_dir))

    def load_experiment_rules(self) -> dict[str, Any]:
        """Load EXPERIMENT_RULES.yaml."""
        p = self.project_root / "tianxing_revision" / "EXPERIMENT_RULES.yaml"
        if p.exists():
            return yaml.safe_load(p.read_text()) or {}
        return {"smoke_first": True, "full_run_requires_confirmation": True}

    def load_execution_env(self) -> dict[str, Any]:
        """Load EXECUTION_ENV.yaml."""
        p = self.project_root / "tianxing_revision" / "EXECUTION_ENV.yaml"
        if p.exists():
            return yaml.safe_load(p.read_text()) or {}
        return {}

    def start_smoke(self, run_id: str, command: str) -> dict[str, Any]:
        """Run a smoke test synchronously (short, blocking)."""
        self.registry.set_runtime_status(run_id, "running")

        log_path = self.log_dir / f"{run_id}_smoke.log"
        code, stdout, stderr = run_cmd(
            ["bash", "-c", command],
            cwd=str(self.project_root),
            timeout=300,
        )

        log_path.write_text(f"=== stdout ===\n{stdout}\n=== stderr ===\n{stderr}\n")

        if code == 0:
            self.registry.set_runtime_status(run_id, "completed")
            return {"ok": True, "log": str(log_path)}
        else:
            self.registry.set_runtime_status(run_id, "failed")
            return {"ok": False, "log": str(log_path), "stderr": stderr[-500:]}

    def start_background(self, run_id: str, command: str) -> dict[str, Any]:
        """Start a background experiment via subprocess.

        For V1, uses subprocess.Popen. V2 will add tmux/slurm support.
        """
        env_config = self.load_execution_env()
        log_path = self.log_dir / f"{run_id}.log"

        self.registry.set_runtime_status(run_id, "running")

        try:
            with open(log_path, "w") as log_file:
                proc = subprocess.Popen(
                    ["bash", "-c", command],
                    cwd=str(env_config.get("working_dir") or self.project_root),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )

            # Record PID for monitoring
            pid_file = self.revision_dir / "locks" / f"{run_id}.pid"
            pid_file.write_text(str(proc.pid))

            return {"ok": True, "pid": proc.pid, "log": str(log_path)}

        except Exception as e:
            self.registry.set_runtime_status(run_id, "failed")
            return {"ok": False, "error": str(e)}

    def check_running(self, run_id: str) -> dict[str, Any]:
        """Check if a background experiment is still running."""
        import os
        import signal

        pid_file = self.revision_dir / "locks" / f"{run_id}.pid"
        if not pid_file.exists():
            return {"running": False, "reason": "no pid file"}

        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)  # Check if process exists
            return {"running": True, "pid": pid}
        except OSError:
            return {"running": False, "pid": pid, "reason": "process exited"}

    def generate_log_summary(self, run_id: str) -> dict[str, Any]:
        """Generate a lightweight log summary for Claude to read."""
        log_path = self.log_dir / f"{run_id}.log"
        if not log_path.exists():
            return {"ok": False, "reason": "no log file"}

        text = log_path.read_text()
        lines = text.splitlines()

        # Extract key sections
        tail = lines[-50:] if len(lines) > 50 else lines
        errors = [l for l in lines if "error" in l.lower() or "Error" in l][:20]
        warnings = [l for l in lines if "warning" in l.lower() or "Warning" in l][:10]

        summary = {
            "run_id": run_id,
            "total_lines": len(lines),
            "tail_50": tail,
            "errors": errors,
            "warnings": warnings,
            "generated_at": iso_now(),
        }

        summary_path = self.summary_dir / f"{run_id}.json"
        atomic_write_json(summary_path, summary)

        return {"ok": True, "summary_path": str(summary_path)}
