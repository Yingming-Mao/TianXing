"""Tests for tianxing.experiment_map."""

import json
import tempfile
from pathlib import Path

import pytest

from tianxing.experiment_map import (
    _scan_tex_file,
    _scan_code,
    _scan_results,
    _infer_links,
    discover_map,
    find_by_path,
    find_code_for_section,
    find_paper_sections_for_code,
    find_tests_for_code,
    load_map,
    merge_maps,
    query_related,
    save_map,
)


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project structure for testing."""
    # Paper
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    (paper_dir / "main.tex").write_text(r"""
\documentclass{article}
\begin{document}

\section{Introduction}\label{sec:intro}
This is the introduction.

\section{Experiments}\label{sec:exp}
We run experiments.

\begin{table}
\caption{Main results}
\label{tab:main}
\begin{tabular}{cc}
a & b
\end{tabular}
\end{table}

\begin{figure}
\includegraphics[width=0.5\textwidth]{results/exp_a/plot.png}
\caption{Ablation study}
\label{fig:ablation}
\end{figure}

See Table \ref{tab:main} and Figure \ref{fig:ablation}.

\end{document}
""")

    # Code
    code_dir = tmp_path / "code"
    code_dir.mkdir()
    exp_a = code_dir / "exp_a"
    exp_a.mkdir()
    (exp_a / "train.py").write_text("# training script")
    (exp_a / "evaluate.py").write_text("# eval script")

    tests_dir = code_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_train.py").write_text("# test for train")

    # Results
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    res_a = results_dir / "exp_a"
    res_a.mkdir()
    (res_a / "metrics.json").write_text('{"accuracy": 0.95}')
    (res_a / "plot.png").write_text("fake png")

    # Config
    (tmp_path / "config.yaml").write_text("""
project:
  paper_dir: paper
  code_dir: code
  results_dir: results
""")

    return tmp_path


def test_scan_tex_file(sample_project):
    tex_path = sample_project / "paper" / "main.tex"
    entities, raw_links = _scan_tex_file(tex_path, sample_project)

    ids = [e["id"] for e in entities]
    assert "sec:intro" in ids
    assert "sec:exp" in ids
    assert "tab:main" in ids
    assert "fig:ablation" in ids

    # Figure should have graphics reference
    fig = next(e for e in entities if e["id"] == "fig:ablation")
    assert "results/exp_a/plot.png" in fig.get("graphics", [])

    # Should have ref links
    assert len(raw_links) > 0


def test_scan_code(sample_project):
    code_entries, test_entries = _scan_code(sample_project / "code", sample_project)

    code_paths = [e["path"] for e in code_entries]
    assert "code/exp_a/train.py" in code_paths
    assert "code/exp_a/evaluate.py" in code_paths

    test_paths = [e["path"] for e in test_entries]
    assert "code/tests/test_train.py" in test_paths


def test_scan_results(sample_project):
    entries = _scan_results(sample_project / "results", sample_project)
    paths = [e["path"] for e in entries]
    assert "results/exp_a/metrics.json" in paths
    assert "results/exp_a/plot.png" in paths

    fig = next(e for e in entries if "plot" in e["path"])
    assert fig["type"] == "figure"


def test_discover_map(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)

    assert len(emap["paper_sections"]) >= 4  # 2 sections + 1 table + 1 figure
    assert len(emap["code_entries"]) >= 2
    assert len(emap["test_entries"]) >= 1
    assert len(emap["result_entries"]) >= 2
    assert len(emap["links"]) > 0


def test_save_and_load(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)
    out_path = save_map(emap, sample_project)
    assert out_path.exists()

    loaded = load_map(sample_project)
    assert loaded is not None
    assert loaded["version"] == "1"
    assert len(loaded["paper_sections"]) == len(emap["paper_sections"])


def test_merge_maps():
    existing = {
        "version": "1",
        "paper_sections": [{"id": "sec:intro", "file": "paper/main.tex", "title": "Intro", "type": "section"}],
        "code_entries": [{"id": "code:train", "path": "code/train.py", "description": "Training (user edited)"}],
        "test_entries": [],
        "result_entries": [],
        "links": [{"from": "sec:intro", "to": "code:train", "relation": "references"}],
    }
    discovered = {
        "version": "1",
        "paper_sections": [
            {"id": "sec:intro", "file": "paper/main.tex", "title": "Introduction", "type": "section", "line_range": [1, 10]},
            {"id": "sec:exp", "file": "paper/main.tex", "title": "Experiments", "type": "section", "line_range": [11, 20]},
        ],
        "code_entries": [{"id": "code:train", "path": "code/train.py", "description": "Code file code/train.py"}],
        "test_entries": [{"id": "test:test_train", "path": "code/tests/test_train.py", "command": "pytest code/tests/test_train.py -x"}],
        "result_entries": [],
        "links": [{"from": "code:train", "to": "test:test_train", "relation": "tested_by"}],
    }

    merged = merge_maps(existing, discovered)

    # New section added
    assert len(merged["paper_sections"]) == 2

    # User description preserved, but line_range updated
    train = next(e for e in merged["code_entries"] if e["id"] == "code:train")
    assert train["description"] == "Training (user edited)"

    # Existing link preserved, new link added
    assert len(merged["links"]) == 2

    # New test entry added
    assert len(merged["test_entries"]) == 1


def test_query_related(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)

    # Query a code entry
    code_entries = [e for e in emap["code_entries"] if "train" in e["id"]]
    assert len(code_entries) > 0
    result = query_related(emap, code_entries[0]["id"])
    assert result["entity"] is not None


def test_find_by_path(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)

    entities = find_by_path(emap, "code/exp_a/train.py")
    assert len(entities) > 0
    assert entities[0]["id"].startswith("code:")


def test_find_tests_for_code(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)

    tests = find_tests_for_code(emap, "code/exp_a/train.py")
    # Should find tests via directory matching or name matching
    assert isinstance(tests, list)


def test_find_code_for_section(sample_project, monkeypatch):
    monkeypatch.chdir(sample_project)
    emap = discover_map(sample_project)

    # The figure references plot.png which is in results/exp_a/
    # And code/exp_a/ produces results/exp_a/
    code = find_code_for_section(emap, "fig:ablation")
    assert isinstance(code, list)
