"""Run tests for the paper's code and report results."""

import argparse
import re

from .utils import ensure_dirs, iso_now, json_result, load_config, run_cmd


def parse_pytest_output(output: str) -> tuple[int, int, list[str]]:
    """Parse pytest output for pass/fail counts."""
    passed = 0
    failed = 0
    errors = []

    m = re.search(r"(\d+) passed", output)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", output)
    if m:
        failed = int(m.group(1))

    for line in output.split("\n"):
        if line.startswith("FAILED") or line.startswith("ERROR"):
            errors.append(line.strip())

    return passed, failed, errors


def main():
    parser = argparse.ArgumentParser(description="Run tests")
    parser.add_argument("--smoke-only", action="store_true", help="Only run smoke tests")
    parser.add_argument("--config", type=str, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    test_cfg = cfg["tests"]

    if not test_cfg.get("enabled", False):
        json_result(True, skipped=True, message="Tests disabled in config (tests.enabled: false)")
        return

    command = test_cfg["command"]
    test_args = test_cfg.get("args", [])
    experiment_env = cfg.get("project", {}).get("env", "")

    cmd = [command] + test_args
    if args.smoke_only and test_cfg.get("smoke_test_dir"):
        cmd.append(test_cfg["smoke_test_dir"])

    code, stdout, stderr = run_cmd(cmd, timeout=300, env=experiment_env)

    # Save log
    timestamp = iso_now().replace(":", "-")
    log_dir = "logs/tests"
    ensure_dirs(log_dir)
    log_file = f"{log_dir}/test_{timestamp}.log"
    with open(log_file, "w") as f:
        f.write(f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}\n")

    combined = stdout + "\n" + stderr
    passed, failed, errors = parse_pytest_output(combined)

    json_result(
        code == 0,
        passed=passed,
        failed=failed,
        errors=errors,
        log_file=log_file,
    )


if __name__ == "__main__":
    main()
