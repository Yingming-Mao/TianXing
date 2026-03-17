"""Collect metrics from results directory."""

import argparse
import json
import re
from pathlib import Path

from .utils import json_result, load_config


def scan_results(results_dir: str) -> dict:
    """Scan results directory for metrics files."""
    results_path = Path(results_dir)
    metrics = {"files_found": [], "tables": [], "figures": []}

    if not results_path.exists():
        metrics["total_files"] = 0
        metrics["total_figures"] = 0
        return metrics

    for f in sorted(results_path.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(results_path))
            metrics["files_found"].append(rel)

            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    metrics["tables"].append({"file": rel, "keys": list(data.keys()) if isinstance(data, dict) else []})
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            elif f.suffix in (".png", ".pdf", ".svg", ".eps"):
                metrics["figures"].append(rel)

    metrics["total_files"] = len(metrics["files_found"])
    metrics["total_figures"] = len(metrics["figures"])
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Collect metrics from results directory")
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--results-dir", type=str, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    results_dir = args.results_dir or cfg["project"].get("results_dir", "results")

    metrics = scan_results(results_dir)
    json_result(True, metrics=metrics)


if __name__ == "__main__":
    main()
