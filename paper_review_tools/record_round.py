"""Record review round artifacts to the reviews/ directory."""

import argparse
import sys
from pathlib import Path

from .utils import ensure_dirs, iso_now, json_result


VALID_TYPES = ("review", "plan", "changes", "validation")


def main():
    parser = argparse.ArgumentParser(description="Record a review round artifact")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument("--type", type=str, required=True, choices=VALID_TYPES, help="Artifact type")
    parser.add_argument("--content-file", type=str, default=None, help="Path to content file")
    args = parser.parse_args()

    # Read content from file or stdin
    if args.content_file:
        content = Path(args.content_file).read_text()
    else:
        if sys.stdin.isatty():
            json_result(False, error="No content provided. Use --content-file or pipe via stdin.")
        content = sys.stdin.read()

    ensure_dirs("reviews")
    filename = f"reviews/round-{args.round:02d}-{args.type}.md"

    header = f"# Round {args.round} — {args.type.title()}\n\n"
    header += f"*Generated: {iso_now()}*\n\n---\n\n"

    with open(filename, "w") as f:
        f.write(header + content)

    json_result(True, file_path=filename)


if __name__ == "__main__":
    main()
