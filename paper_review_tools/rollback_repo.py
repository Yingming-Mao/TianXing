"""Roll back the repo to a previous checkpoint."""

import argparse

from .utils import git_hash, json_result, run_cmd


def main():
    parser = argparse.ArgumentParser(description="Roll back to a git checkpoint")
    parser.add_argument("--target", type=str, required=True, help="Tag or commit to roll back to")
    args = parser.parse_args()

    # Verify target exists
    code, _, _ = run_cmd(["git", "rev-parse", "--verify", args.target])
    if code != 0:
        json_result(False, error=f"Target not found: {args.target}")

    previous_head = git_hash()

    code, _, err = run_cmd(["git", "reset", "--hard", args.target])
    if code != 0:
        json_result(False, error=f"Failed to reset: {err}")

    json_result(True, rolled_back_to=args.target, previous_head=previous_head)


if __name__ == "__main__":
    main()
