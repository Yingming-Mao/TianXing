"""Create a git checkpoint (tag) before a review round."""

import argparse

from .utils import git_hash, git_is_clean, json_result, load_config, run_cmd


def main():
    parser = argparse.ArgumentParser(description="Checkpoint the repo before a review round")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument("--message", type=str, default="", help="Commit message for dirty files")
    parser.add_argument("--config", type=str, default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    prefix = cfg["git"]["tag_prefix"]
    tag = f"{prefix}{args.round}-start"

    # Check git availability
    code, _, err = run_cmd(["git", "rev-parse", "--git-dir"])
    if code != 0:
        json_result(False, error="Not a git repository")

    dirty_files = []
    if not git_is_clean():
        # Commit dirty files
        code, out, _ = run_cmd(["git", "status", "--porcelain"])
        dirty_files = [line.strip() for line in out.strip().split("\n") if line.strip()]
        msg = args.message or f"auto-checkpoint before review round {args.round}"
        run_cmd(["git", "add", "-A"])
        code, _, err = run_cmd(["git", "commit", "-m", msg])
        if code != 0:
            json_result(False, error=f"Failed to commit: {err}")

    # Create tag
    commit = git_hash()
    code, _, err = run_cmd(["git", "tag", "-f", tag])
    if code != 0:
        json_result(False, error=f"Failed to create tag: {err}")

    json_result(True, tag=tag, commit=commit, dirty_files=dirty_files)


if __name__ == "__main__":
    main()
