from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .browser import default_profile_dir, run_browser
from .cli import parse_args
from .keywords import load_keyword_file, load_keyword_rules
from .models import BrowserName, BrowserOptions, MatchMode, ScanOptions, Target


def build_runtime(args: argparse.Namespace) -> tuple[BrowserOptions, ScanOptions, set[str], set[str], list[Target]]:
    rules = load_keyword_rules(args.keyword_profiles, args.exclude_mode)
    extra_keywords = load_keyword_file(args.keywords_file)
    keywords = set() if args.only_keywords_file else set(rules.political_keywords)
    hashtags = set() if args.only_keywords_file else set(rules.political_hashtags)
    keywords.update(extra_keywords)

    match_mode = MatchMode(args.match)
    if match_mode == MatchMode.POLITICS and not keywords and not hashtags:
        raise ValueError("No political keywords or hashtags configured.")

    browser_options = BrowserOptions(
        browser=BrowserName(args.browser),
        profile_dir=args.browser_profile_dir,
        channel=args.browser_channel,
        executable_path=args.executable_path,
        connect_cdp=args.connect_cdp,
        login=args.login,
        headless=args.headless,
    )
    scan_options = ScanOptions(
        profile_url=args.profile_url,
        target=Target(args.target),
        match_mode=match_mode,
        max_posts=args.max_posts,
        delete=args.delete,
        delete_all=args.delete_all,
        pause=args.pause,
        exclusion_mode=args.exclude_mode,
        exclusion_keywords=rules.exclusion_keywords,
        exclusion_hashtags=rules.exclusion_hashtags,
    )
    targets = [Target.POSTS] if args.delete_all else [Target(args.target)]
    return browser_options, scan_options, keywords, hashtags, targets


def print_run_summary(
    browser_options: BrowserOptions,
    scan_options: ScanOptions,
    keywords: set[str],
) -> None:
    print(f"Mode: {'DELETE' if scan_options.delete else 'DRY RUN'}")
    if browser_options.connect_cdp:
        print(f"Browser: existing Chrome/Chromium via CDP at {browser_options.connect_cdp}")
    else:
        print(f"Browser: {browser_options.browser.value}")
        if browser_options.channel:
            print(f"Browser channel: {browser_options.channel}")
        if browser_options.executable_path:
            print(f"Executable: {browser_options.executable_path}")
        print(f"Profile: {browser_options.profile_dir or default_profile_dir(browser_options.browser)}")

    target_label = "reposts and owned posts/replies" if scan_options.delete_all else scan_options.target.value
    print(f"Target: {target_label}")
    print(f"Match: {scan_options.match_mode.value}")
    if scan_options.exclusion_mode:
        print(
            f"Exclusions: {scan_options.exclusion_mode} "
            f"({len(scan_options.exclusion_keywords)} keywords, "
            f"{len(scan_options.exclusion_hashtags)} hashtags)"
        )
    print(f"Scan limit: {scan_options.max_posts if scan_options.max_posts is not None else 'entire timeline'}")
    if scan_options.match_mode == MatchMode.POLITICS:
        print(f"Keywords loaded: {len(keywords)}")
    print("Use Ctrl+C to stop at any time.")


def print_results(
    results: dict[Target, tuple[int, int]],
    targets: list[Target],
    delete_all: bool,
) -> None:
    for target in targets:
        scanned, removed = results[target]
        if delete_all:
            print(f"Done: scanned {scanned} actionable items; removed {removed}.")
            continue
        action = "unreposted" if target == Target.RETWEETS else "deleted"
        print(f"Done: scanned {scanned} {target.value}; {action} {removed}.")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        browser_options, scan_options, keywords, hashtags, targets = build_runtime(args)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print_run_summary(browser_options, scan_options, keywords)
    try:
        results = run_browser(browser_options, scan_options, keywords, hashtags, targets)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print_results(results, targets, scan_options.delete_all)
    return 0

