"""Integration tests for tianxing CLI modules."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def run_module(module: str, args: list[str], cwd: str = None) -> tuple[int, dict]:
    """Run a tianxing module and parse JSON output."""
    cmd = ["python", "-m", f"tianxing.{module}"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        data = {"raw_stdout": r.stdout, "raw_stderr": r.stderr}
    return r.returncode, data


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    # Initial commit
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


def test_checkpoint_repo(git_repo):
    code, data = run_module("checkpoint_repo", ["--round", "1"], cwd=str(git_repo))
    assert code == 0
    assert data["ok"] is True
    assert data["tag"] == "review-round-1-start"
    assert len(data["commit"]) > 0


def test_checkpoint_with_dirty_files(git_repo):
    (git_repo / "new_file.txt").write_text("hello")
    code, data = run_module("checkpoint_repo", ["--round", "2"], cwd=str(git_repo))
    assert code == 0
    assert data["ok"] is True
    assert len(data["dirty_files"]) > 0


def test_rollback_repo(git_repo):
    # Create checkpoint
    run_module("checkpoint_repo", ["--round", "1"], cwd=str(git_repo))
    # Make a change
    (git_repo / "change.txt").write_text("change")
    subprocess.run(["git", "add", "-A"], cwd=git_repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "change"], cwd=git_repo, capture_output=True)
    # Rollback
    code, data = run_module("rollback_repo", ["--target", "review-round-1-start"], cwd=str(git_repo))
    assert code == 0
    assert data["ok"] is True
    assert not (git_repo / "change.txt").exists()


def test_record_round(tmp_path):
    content_file = tmp_path / "review.json"
    content_file.write_text('{"score": 7.5, "issues": []}')
    code, data = run_module("record_round", [
        "--round", "1", "--type", "review", "--content-file", str(content_file)
    ], cwd=str(tmp_path))
    assert code == 0
    assert data["ok"] is True
    assert (tmp_path / "reviews" / "round-01-review.md").exists()


def test_update_status(tmp_path):
    code, data = run_module("update_status", [
        "--round", "1", "--phase", "review", "--score", "6.5"
    ], cwd=str(tmp_path))
    assert code == 0
    assert data["ok"] is True
    assert data["status"]["score"] == 6.5
    assert (tmp_path / "status" / "current.json").exists()
    assert (tmp_path / "status" / "history.jsonl").exists()


def test_update_status_delta(tmp_path):
    # First update
    run_module("update_status", ["--round", "1", "--phase", "complete", "--score", "5.0"], cwd=str(tmp_path))
    # Second update
    code, data = run_module("update_status", ["--round", "2", "--phase", "complete", "--score", "7.0"], cwd=str(tmp_path))
    assert code == 0
    assert data["status"]["score_delta"] == 2.0


def test_notify_status(tmp_path):
    code, data = run_module("notify_status", [
        "--level", "info", "--message", "Test notification", "--round", "1"
    ], cwd=str(tmp_path))
    assert code == 0
    assert data["ok"] is True
    assert "notification_file" in data


def test_collect_metrics_empty(tmp_path):
    code, data = run_module("collect_metrics", ["--results-dir", str(tmp_path / "results")], cwd=str(tmp_path))
    assert code == 0
    assert data["ok"] is True
    assert data["metrics"]["total_files"] == 0


def test_collect_metrics_with_files(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "data.json").write_text('{"accuracy": 0.95}')
    (results_dir / "plot.png").write_text("fake png")
    code, data = run_module("collect_metrics", ["--results-dir", str(results_dir)], cwd=str(tmp_path))
    assert code == 0
    assert data["metrics"]["total_files"] == 2
    assert data["metrics"]["total_figures"] == 1
