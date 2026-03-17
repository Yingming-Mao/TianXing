"""TianXing — automated review and improvement for academic papers."""

import sys
import importlib

__version__ = "0.1.0"

COMMANDS = {
    "checkpoint": "tianxing.checkpoint_repo",
    "rollback": "tianxing.rollback_repo",
    "compile": "tianxing.compile_paper",
    "test": "tianxing.run_tests",
    "record": "tianxing.record_round",
    "status": "tianxing.update_status",
    "notify": "tianxing.notify_status",
    "metrics": "tianxing.collect_metrics",
    "map": "tianxing.experiment_map",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"tianxing v{__version__}")
        print(f"\nAvailable commands: {', '.join(sorted(COMMANDS))}")
        print("\nUsage: tianxing <command> [args...]")
        print("   or: python -m tianxing.<module> [args...]")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(sorted(COMMANDS))}")
        sys.exit(1)

    # Remove 'tianxing' and the command name, keep the rest
    sys.argv = [COMMANDS[cmd]] + sys.argv[2:]
    mod = importlib.import_module(COMMANDS[cmd])
    if hasattr(mod, "main"):
        mod.main()
