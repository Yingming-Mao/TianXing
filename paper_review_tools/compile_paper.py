"""Compile a LaTeX paper and report results."""

import argparse
import re
from pathlib import Path

from .utils import ensure_dirs, iso_now, json_result, load_config, run_cmd


def parse_latex_log(log_text: str) -> tuple[list[str], list[str]]:
    """Extract errors and warnings from LaTeX log output."""
    errors = []
    warnings = []
    for line in log_text.split("\n"):
        if line.startswith("!") or "Fatal error" in line:
            errors.append(line.strip())
        elif re.search(r"Warning:", line, re.IGNORECASE):
            warnings.append(line.strip())
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Compile LaTeX paper")
    parser.add_argument("--config", type=str, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    compile_cfg = cfg["compile"]
    main_file = compile_cfg["main_file"]

    if not Path(main_file).exists():
        json_result(False, error=f"Main file not found: {main_file}")

    engine = compile_cfg["engine"]
    cmd_args = compile_cfg.get("args", ["-pdf", "-interaction=nonstopmode"])
    cmd = [engine] + cmd_args + [main_file]

    # Run compilation
    code, stdout, stderr = run_cmd(cmd, timeout=120)

    # Save log
    timestamp = iso_now().replace(":", "-")
    log_dir = "logs/latex"
    ensure_dirs(log_dir)
    log_file = f"{log_dir}/compile_{timestamp}.log"
    with open(log_file, "w") as f:
        f.write(f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}\n")

    combined = stdout + "\n" + stderr
    errors, warnings = parse_latex_log(combined)

    pdf_path = main_file.replace(".tex", ".pdf")
    if not Path(pdf_path).exists():
        pdf_path = ""

    json_result(
        code == 0,
        errors=errors,
        warnings=warnings,
        pdf_path=pdf_path if Path(pdf_path).exists() else "",
        log_file=log_file,
    )


if __name__ == "__main__":
    main()
