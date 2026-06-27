#!/usr/bin/env python3
"""Command-line entrypoint for Twit Delete."""

import sys

try:
    from twit_cleaner.app import main
except ModuleNotFoundError as exc:
    if exc.name != "playwright":
        raise
    print(
        "Playwright is not installed for this Python environment.\n\n"
        "Run:\n"
        "  python3 -m pip install -r requirements.txt\n"
        "  python3 -m playwright install chromium\n",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


if __name__ == "__main__":
    raise SystemExit(main())
