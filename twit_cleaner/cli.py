from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .constants import DEFAULT_KEYWORD_PROFILES_PATH
from .models import BrowserName, ExclusionMode, MatchMode, Target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete X/Twitter posts that look political by navigating the website."
    )
    parser.add_argument("--profile-url", required=True, help="Profile URL to scan, e.g. https://x.com/me")
    parser.add_argument(
        "--max-posts",
        type=int,
        help="Optional maximum number of post cards to inspect. By default, scan the entire timeline.",
    )
    parser.add_argument("--delete", action="store_true", help="Actually delete matched posts")
    parser.add_argument("--headless", action="store_true", help="Run browser without a visible window")
    parser.add_argument(
        "--browser",
        choices=[browser.value for browser in BrowserName],
        default=BrowserName.CHROMIUM.value,
        help="Browser engine to use.",
    )
    parser.add_argument(
        "--browser-profile-dir",
        type=Path,
        help="Persistent browser profile directory. Can point at a Firefox profile if Firefox is closed.",
    )
    parser.add_argument(
        "--browser-channel",
        choices=["chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "chromium"],
        help="Installed Chromium-family browser channel to launch, e.g. chrome or chromium.",
    )
    parser.add_argument(
        "--executable-path",
        type=Path,
        help="Path to a browser executable to launch instead of Playwright's bundled browser.",
    )
    parser.add_argument(
        "--connect-cdp",
        help="Connect to an already-running Chrome/Chromium over CDP, e.g. http://127.0.0.1:9222.",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open X login first and wait for Enter in the terminal before scanning.",
    )
    parser.add_argument(
        "--target",
        choices=[target.value for target in Target],
        default=Target.POSTS.value,
        help="Timeline item type to scan/delete.",
    )
    parser.add_argument(
        "--match",
        choices=[mode.value for mode in MatchMode],
        default=MatchMode.POLITICS.value,
        help="Delete only political matches, or every item in the selected target.",
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all posts and replies, and undo all reposts, regardless of content.",
    )
    parser.add_argument(
        "--delete-all-posts",
        action="store_true",
        help="Shortcut for --target posts --match all --delete.",
    )
    parser.add_argument(
        "--delete-all-replies",
        action="store_true",
        help="Shortcut for --target replies --match all --delete.",
    )
    parser.add_argument(
        "--delete-all-retweets",
        "--unretweet-all",
        dest="delete_all_retweets",
        action="store_true",
        help="Undo every repost made by the logged-in account.",
    )
    parser.add_argument(
        "--include-replies",
        action="store_true",
        help="Deprecated alias for --target replies.",
    )
    parser.add_argument(
        "--keywords-file",
        type=Path,
        help="Text file with extra political keywords, one per line. Lines starting with # are ignored.",
    )
    parser.add_argument(
        "--keyword-profiles",
        type=Path,
        default=DEFAULT_KEYWORD_PROFILES_PATH,
        help="JSON file containing political terms and exclusion profiles.",
    )
    parser.add_argument(
        "--exclude-mode",
        choices=[mode.value for mode in ExclusionMode],
        help="Keep posts/replies matching the personal, work, or custom exclusion profile.",
    )
    parser.add_argument(
        "--only-keywords-file",
        action="store_true",
        help="Use only --keywords-file keywords instead of the built-in list.",
    )
    parser.add_argument("--pause", type=float, default=0.8, help="Seconds to pause between browser actions")
    return parser


def apply_shortcuts(args: argparse.Namespace) -> argparse.Namespace:
    shortcuts = [
        (args.delete_all_posts, Target.POSTS.value, "--delete-all-posts"),
        (args.delete_all_replies, Target.REPLIES.value, "--delete-all-replies"),
        (args.delete_all_retweets, Target.RETWEETS.value, "--delete-all-retweets"),
    ]
    enabled = [(target, flag) for is_enabled, target, flag in shortcuts if is_enabled]
    if args.delete_all and enabled:
        flags = ", ".join(flag for _, flag in enabled)
        raise ValueError(f"Do not combine --delete-all with category shortcuts: {flags}")
    if len(enabled) > 1:
        flags = ", ".join(flag for _, flag in enabled)
        raise ValueError(f"Use only one delete-all shortcut at a time: {flags}")

    if args.delete_all:
        args.match = MatchMode.ALL.value
        args.delete = True
    elif enabled:
        args.target = enabled[0][0]
        args.match = MatchMode.ALL.value
        args.delete = True
    elif args.include_replies:
        args.target = Target.REPLIES.value
    return args


def validate_args(args: argparse.Namespace) -> None:
    if args.login and args.headless:
        raise ValueError("--login requires a visible browser; remove --headless.")
    if args.connect_cdp and args.login:
        raise ValueError("--connect-cdp uses an already-running browser; do not pass --login.")
    if args.connect_cdp and (
        args.browser_profile_dir or args.browser_channel or args.executable_path or args.headless
    ):
        raise ValueError(
            "--connect-cdp cannot be combined with --browser-profile-dir, --browser-channel, "
            "--executable-path, or --headless."
        )
    if args.browser_channel and BrowserName(args.browser) != BrowserName.CHROMIUM:
        raise ValueError("--browser-channel is only supported with --browser chromium.")
    if args.browser_channel and args.executable_path:
        raise ValueError("Use either --browser-channel or --executable-path, not both.")
    if args.only_keywords_file and not args.keywords_file:
        raise ValueError("--only-keywords-file requires --keywords-file")
    if args.max_posts is not None and args.max_posts < 1:
        raise ValueError("--max-posts must be at least 1")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    args = apply_shortcuts(build_parser().parse_args(argv))
    validate_args(args)
    return args

