"""Update the review status tracker."""

import argparse
import json
from pathlib import Path

from .utils import ensure_dirs, iso_now, json_result


def main():
    parser = argparse.ArgumentParser(description="Update review status")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument("--phase", type=str, required=True, help="Current phase")
    parser.add_argument("--score", type=float, default=None, help="Review score")
    parser.add_argument("--message", type=str, default="", help="Status message")
    args = parser.parse_args()

    ensure_dirs("status")
    current_file = Path("status/current.json")
    history_file = Path("status/history.jsonl")

    # Build status entry
    entry = {
        "round": args.round,
        "phase": args.phase,
        "score": args.score,
        "message": args.message,
        "timestamp": iso_now(),
    }

    # Load existing status to compute delta
    if current_file.exists():
        prev = json.loads(current_file.read_text())
        if args.score is not None and prev.get("score") is not None:
            entry["score_delta"] = round(args.score - prev["score"], 2)

    # Write current
    current_file.write_text(json.dumps(entry, ensure_ascii=False, indent=2))

    # Append to history
    with open(history_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    json_result(True, status=entry)


if __name__ == "__main__":
    main()
