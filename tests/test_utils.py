"""Tests for tianxing.utils."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tianxing.utils import (
    _deep_merge,
    ensure_dirs,
    find_config,
    iso_now,
    load_config,
    run_cmd,
)


def test_deep_merge():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}, "e": 5}
    result = _deep_merge(base, override)
    assert result == {"a": 1, "b": {"c": 99, "d": 3}, "e": 5}


def test_run_cmd_success():
    code, out, err = run_cmd(["echo", "hello"])
    assert code == 0
    assert out.strip() == "hello"


def test_run_cmd_not_found():
    code, out, err = run_cmd(["nonexistent_command_xyz"])
    assert code == -1
    assert "not found" in err.lower()


def test_run_cmd_timeout():
    code, out, err = run_cmd(["sleep", "10"], timeout=1)
    assert code == -1
    assert "timed out" in err.lower()


def test_ensure_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = os.path.join(tmpdir, "a", "b")
        p2 = os.path.join(tmpdir, "c")
        ensure_dirs(p1, p2)
        assert Path(p1).is_dir()
        assert Path(p2).is_dir()


def test_iso_now():
    ts = iso_now()
    assert "T" in ts
    assert "+" in ts or "Z" in ts


def test_load_config_defaults():
    cfg = load_config("/nonexistent/path.yaml")
    assert cfg["compile"]["engine"] == "latexmk"
    assert cfg["review"]["max_rounds"] == 3


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"project": {"name": "test-paper"}, "review": {"max_rounds": 5}}, f)
        f.flush()
        cfg = load_config(f.name)
    os.unlink(f.name)
    assert cfg["project"]["name"] == "test-paper"
    assert cfg["review"]["max_rounds"] == 5
    # defaults still present
    assert cfg["compile"]["engine"] == "latexmk"


def test_find_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("project:\n  name: test\n")
        subdir = Path(tmpdir) / "sub" / "deep"
        subdir.mkdir(parents=True)
        with patch("tianxing.utils.Path.cwd", return_value=subdir):
            found = find_config()
            assert found == config_path
