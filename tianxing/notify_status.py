"""Send status notifications (V1: file-based only)."""

import argparse
import json

from .utils import ensure_dirs, iso_now, json_result


def main():
    parser = argparse.ArgumentParser(description="Send a status notification")
    parser.add_argument("--level", type=str, default="info", choices=["info", "warn", "error", "success"])
    parser.add_argument("--message", type=str, required=True, help="Notification message")
    parser.add_argument("--round", type=int, default=None)
    args = parser.parse_args()

    ensure_dirs("logs/notifications")

    timestamp = iso_now()
    safe_ts = timestamp.replace(":", "-")
    notification = {
        "level": args.level,
        "message": args.message,
        "round": args.round,
        "timestamp": timestamp,
    }

    filename = f"logs/notifications/notify_{safe_ts}.json"
    with open(filename, "w") as f:
        json.dump(notification, f, ensure_ascii=False, indent=2)

    json_result(True, notification_file=filename)


if __name__ == "__main__":
    main()
