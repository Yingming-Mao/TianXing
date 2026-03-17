"""Paper Review Tools — automated review and improvement for academic papers."""

import sys
import importlib

__version__ = "0.1.0"

COMMANDS = {
    "checkpoint": "paper_review_tools.checkpoint_repo",
    "rollback": "paper_review_tools.rollback_repo",
    "compile": "paper_review_tools.compile_paper",
    "test": "paper_review_tools.run_tests",
    "record": "paper_review_tools.record_round",
    "status": "paper_review_tools.update_status",
    "notify": "paper_review_tools.notify_status",
    "metrics": "paper_review_tools.collect_metrics",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"paper-review-tools v{__version__}")
        print(f"\nAvailable commands: {', '.join(sorted(COMMANDS))}")
        print("\nUsage: paper-review-tools <command> [args...]")
        print("   or: python -m paper_review_tools.<module> [args...]")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(sorted(COMMANDS))}")
        sys.exit(1)

    # Remove 'paper-review-tools' and the command name, keep the rest
    sys.argv = [COMMANDS[cmd]] + sys.argv[2:]
    mod = importlib.import_module(COMMANDS[cmd])
    if hasattr(mod, "main"):
        mod.main()
