"""Tests for revision setup scaffolding."""

import json
import pytest
from pathlib import Path

from tianxing.revision.revision_setup import setup, INPUT_DIR, RUNTIME_DIR


class TestSetup:
    def test_creates_directories(self, tmp_path):
        result = setup(tmp_path)
        assert (tmp_path / INPUT_DIR).is_dir()
        assert (tmp_path / RUNTIME_DIR).is_dir()
        assert (tmp_path / RUNTIME_DIR / "artifacts").is_dir()
        assert (tmp_path / RUNTIME_DIR / "logs").is_dir()
        assert (tmp_path / RUNTIME_DIR / "locks").is_dir()

    def test_creates_input_templates(self, tmp_path):
        setup(tmp_path)
        assert (tmp_path / INPUT_DIR / "REVISION_SPEC.md").exists()
        assert (tmp_path / INPUT_DIR / "SUCCESS_CRITERIA.md").exists()
        assert (tmp_path / INPUT_DIR / "EXPERIMENT_RULES.yaml").exists()
        assert (tmp_path / INPUT_DIR / "EXECUTION_ENV.yaml").exists()
        assert (tmp_path / INPUT_DIR / "CLAIMS_TO_PRESERVE.md").exists()
        assert (tmp_path / INPUT_DIR / "OPERATOR_NOTES.md").exists()
        assert (tmp_path / INPUT_DIR / "MANUAL_OVERRIDES.yaml").exists()

    def test_creates_state_files(self, tmp_path):
        setup(tmp_path)
        for name in [
            "state.json", "knowledge_state.json", "decision_state.json",
            "master_plan.json", "task_registry.json", "result_registry.json",
            "claim_registry.json", "observations.json",
        ]:
            path = tmp_path / RUNTIME_DIR / name
            assert path.exists(), f"Missing: {name}"
            data = json.loads(path.read_text())
            assert "schema_version" in data

    def test_idempotent(self, tmp_path):
        r1 = setup(tmp_path)
        r2 = setup(tmp_path)
        # Second run should not overwrite existing files
        assert len(r2["created_files"]) == 0

    def test_returns_paths(self, tmp_path):
        result = setup(tmp_path)
        assert "input_dir" in result
        assert "runtime_dir" in result
        assert "created_files" in result
        assert len(result["created_files"]) > 0
