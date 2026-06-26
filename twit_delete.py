#!/usr/bin/env python3
"""
Delete your own X/Twitter posts that appear to be about politics.

The bot navigates the website with Playwright instead of using the API. It is
dry-run by default; pass --delete to perform destructive actions.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

try:
    from playwright.sync_api import BrowserContext, Locator, Page, TimeoutError, sync_playwright
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


DEFAULT_POLITICAL_KEYWORDS = {
    "russia",
    "ukraine",
    "brasil",
    "brazil",
    "esquerda",
    "direita",
    "abortion",
    "biden",
    "bolsonaro",
    "congress",
    "conservative",
    "democrat",
    "democratic",
    "election",
    "electoral",
    "fascism",
    "fascist",
    "governador",
    "governor",
    "impeachment",
    "leftist",
    "liberal",
    "lula",
    "maga",
    "mayor",
    "minister",
    "ministro",
    "parliament",
    "politica",
    "política",
    "president",
    "prime minister",
    "progressive",
    "republican",
    "right-wing",
    "senate",
    "senator",
    "socialism",
    "socialist",
    "stf",
    "supreme court",
    "trump",
    "vaccine mandate",
    "white house",
}

DEFAULT_POLITICAL_HASHTAGS = {
    "biden2024",
    "bolsonaro",
    "democrats",
    "elections",
    "eleicoes",
    "fakenews",
    "fora",
    "impeachment",
    "lula",
    "maga",
    "politica",
    "politics",
    "republicans",
    "trump2024",
}

MENU_LABELS = [
    "More",
    "Mais",
    "More options",
    "Mais opcoes",
    "Mais opções",
]

DELETE_LABELS = [
    "Delete",
    "Excluir",
    "Delete post",
    "Excluir post",
    "Delete Tweet",
    "Excluir Tweet",
]

CONFIRM_DELETE_LABELS = [
    "Delete",
    "Excluir",
]

UNREPOST_LABELS = [
    "Undo repost",
    "Undo reposts",
    "Undo Retweet",
    "Desfazer repostagem",
    "Desfazer repost",
    "Desfazer Retweet",
]


class Target(str, Enum):
    POSTS = "posts"
    REPLIES = "replies"
    RETWEETS = "retweets"


class MatchMode(str, Enum):
    POLITICS = "politics"
    ALL = "all"


class BrowserName(str, Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PostKind:
    is_reply: bool
    is_retweet: bool


def parse_args() -> argparse.Namespace:
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
        action="store_true",
        help="Shortcut for --target retweets --match all --delete.",
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
        "--only-keywords-file",
        action="store_true",
        help="Use only --keywords-file keywords instead of the built-in list.",
    )
    parser.add_argument("--pause", type=float, default=0.8, help="Seconds to pause between browser actions")
    return parser.parse_args()


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


def timeline_url(profile_url: str, target: Target) -> str:
    if target != Target.REPLIES:
        return profile_url

    parsed = urlsplit(profile_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/with_replies"):
        return profile_url
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/with_replies", "", ""))


def origin_from_url(profile_url: str) -> str:
    parsed = urlsplit(profile_url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or "x.com"
    return urlunsplit((scheme, netloc, "", "", ""))


def default_profile_dir(browser: BrowserName) -> Path:
    if browser == BrowserName.FIREFOX:
        return Path(".browser-profile-firefox")
    return Path(".browser-profile")


def browser_type(playwright, browser: BrowserName):
    if browser == BrowserName.FIREFOX:
        return playwright.firefox
    return playwright.chromium


def load_keywords(path: Path | None, only_file: bool) -> set[str]:
    keywords: set[str] = set() if only_file else set(DEFAULT_POLITICAL_KEYWORDS)
    if not path:
        return keywords

    for line in path.read_text(encoding="utf-8").splitlines():
        keyword = line.strip().lower()
        if keyword and not keyword.startswith("#"):
            keywords.add(keyword)
    return keywords


def keyword_regex(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword)
    if re.match(r"^[\w -]+$", keyword, flags=re.IGNORECASE):
        escaped = escaped.replace(r"\ ", r"\s+")
        return re.compile(rf"(?<!\w){escaped}(?!\w)", flags=re.IGNORECASE)
    return re.compile(escaped, flags=re.IGNORECASE)


def classify_post(text: str, keywords: Iterable[str], hashtags: set[str]) -> MatchResult:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    reasons: list[str] = []

    for hashtag in re.findall(r"#([\w_]+)", lowered):
        if hashtag in hashtags:
            reasons.append(f"hashtag #{hashtag}")

    for keyword in sorted(keywords):
        if keyword_regex(keyword).search(normalized):
            reasons.append(f"keyword '{keyword}'")

    return MatchResult(bool(reasons), tuple(reasons[:8]))


def first_visible_by_labels(scope: Page | Locator, role: str, labels: Iterable[str], timeout: int = 600) -> Locator | None:
    for label in labels:
        try:
            locator = scope.get_by_role(role, name=re.compile(rf"^{re.escape(label)}$", re.IGNORECASE))
            if locator.first.is_visible(timeout=timeout):
                return locator.first
        except TimeoutError:
            continue
    return None


def post_text(article: Locator) -> str:
    try:
        text_nodes = article.locator('[data-testid="tweetText"]')
        count = text_nodes.count()
        if count:
            return "\n".join(text_nodes.nth(index).inner_text(timeout=1500) for index in range(count))
    except TimeoutError:
        pass
    return article.inner_text(timeout=2000)


def post_fingerprint(article: Locator, fallback_text: str = "") -> str:
    status_links = article.locator('a[href*="/status/"]')
    for index in range(status_links.count()):
        href = status_links.nth(index).get_attribute("href")
        if href and "/status/" in href:
            return href.split("?")[0]
    if fallback_text:
        return " ".join(fallback_text.split())
    return " ".join(article.inner_text(timeout=2000).split())


def post_kind(article: Locator) -> PostKind:
    text = " ".join(article.inner_text(timeout=2000).split()).lower()
    is_reply = any(marker in text for marker in ("replying to", "em resposta a", "respondendo a"))
    is_retweet = any(
        marker in text
        for marker in (
            "reposted",
            "repostou",
            "retweeted",
            "retweetou",
            "you reposted",
            "voce repostou",
            "você repostou",
        )
    )
    return PostKind(is_reply=is_reply, is_retweet=is_retweet)


def matches_target(kind: PostKind, target: Target) -> bool:
    if target == Target.RETWEETS:
        return kind.is_retweet
    if target == Target.REPLIES:
        return not kind.is_retweet
    return not kind.is_reply and not kind.is_retweet


def wait_for_profile_content(page: Page, timeout_ms: int = 60_000) -> None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    status_text = re.compile(
        r"hasn.t posted|These posts are protected|Account suspended|This account doesn't exist|"
        r"Esses posts est[aã]o protegidos|Conta suspensa|Esta conta n[aã]o existe",
        flags=re.IGNORECASE,
    )

    while time.monotonic() < deadline:
        if page.locator("article").count() > 0:
            return
        if page.locator('[data-testid="loginButton"]').count() > 0:
            return
        if page.locator('a[href="/login"]').count() > 0:
            return
        if page.get_by_text(status_text).count() > 0:
            return
        time.sleep(0.5)

    raise RuntimeError(
        "Timed out waiting for X profile content. "
        "Make sure you are logged in, the profile URL is correct, and the page is reachable."
    )


def login_if_requested(page: Page, profile_url: str, should_login: bool) -> None:
    if not should_login:
        return

    login_url = f"{origin_from_url(profile_url)}/login"
    print(f"Opening login page: {login_url}")
    page.goto(login_url, wait_until="domcontentloaded", timeout=60_000)
    print("Log in in the browser window, then come back here and press Enter to continue.")
    input()


def open_profile(page: Page, profile_url: str, target: Target, allow_empty: bool = False) -> None:
    page.goto(timeline_url(profile_url, target), wait_until="domcontentloaded", timeout=60_000)
    wait_for_profile_content(page)

    if page.locator("article").count() == 0:
        if allow_empty:
            return
        if target == Target.REPLIES:
            empty_hint = "The Replies tab is empty or X did not expose reply cards for this account."
        elif target == Target.RETWEETS:
            empty_hint = "The main timeline is empty, so no repost cards were available to inspect."
        else:
            empty_hint = "The main Posts tab is empty. Try --target replies or --target retweets if needed."
        raise RuntimeError(
            "The profile loaded, but no post cards were found. "
            f"{empty_hint} If X is showing a login screen or logged-out view, run again with --login."
        )


def delete_post(page: Page, article: Locator, pause: float) -> bool:
    menu_button = first_visible_by_labels(article, "button", MENU_LABELS)
    if not menu_button:
        print("  skip: post menu not found")
        return False

    menu_button.click()
    time.sleep(pause)

    delete_item = first_visible_by_labels(page, "menuitem", DELETE_LABELS, timeout=1200)
    if not delete_item:
        delete_item = first_visible_by_labels(page, "button", DELETE_LABELS, timeout=1200)
    if not delete_item:
        page.keyboard.press("Escape")
        print("  skip: delete action not found")
        return False

    delete_item.click()
    time.sleep(pause)

    confirm_button = first_visible_by_labels(page, "button", CONFIRM_DELETE_LABELS, timeout=2500)
    if not confirm_button:
        page.keyboard.press("Escape")
        print("  skip: confirmation button not found")
        return False

    confirm_button.click()
    time.sleep(pause)
    return True


def undo_retweet(page: Page, article: Locator, pause: float) -> bool:
    repost_button = article.locator('[data-testid="retweet"]').first
    try:
        if not repost_button.is_visible(timeout=1200):
            print("  skip: repost button not found")
            return False
    except TimeoutError:
        print("  skip: repost button not found")
        return False

    repost_button.click()
    time.sleep(pause)

    undo_item = first_visible_by_labels(page, "menuitem", UNREPOST_LABELS, timeout=1800)
    if not undo_item:
        undo_item = first_visible_by_labels(page, "button", UNREPOST_LABELS, timeout=1800)
    if not undo_item:
        page.keyboard.press("Escape")
        print("  skip: undo repost action not found")
        return False

    undo_item.click()
    time.sleep(pause)
    return True


def remove_item(page: Page, article: Locator, target: Target, pause: float) -> bool:
    if target == Target.RETWEETS:
        return undo_retweet(page, article, pause)
    return delete_post(page, article, pause)


def scan_and_maybe_delete(
    page: Page,
    args: argparse.Namespace,
    keywords: set[str],
    hashtags: set[str],
) -> tuple[int, int]:
    scanned = 0
    removed = 0
    seen_cards: set[str] = set()
    target = Target(args.target)
    match_mode = MatchMode(args.match)
    idle_scrolls = 0
    max_idle_scrolls = 5

    def limit_reached() -> bool:
        return args.max_posts is not None and scanned >= args.max_posts

    while not limit_reached():
        articles = page.locator("article")
        article_count = articles.count()
        made_progress = False
        processed_item = False

        for index in range(article_count):
            if limit_reached():
                break

            article = articles.nth(index)
            try:
                fingerprint = post_fingerprint(article)
            except TimeoutError:
                continue

            if not fingerprint or fingerprint in seen_cards:
                continue

            seen_cards.add(fingerprint)
            made_progress = True

            try:
                kind = post_kind(article)
            except TimeoutError:
                continue
            if not matches_target(kind, target):
                continue

            scanned += 1
            processed_item = True
            if match_mode == MatchMode.ALL:
                action = "undoing repost" if target == Target.RETWEETS else "deleting"
                dry_run_action = "undo repost" if target == Target.RETWEETS else "delete"
                if args.delete:
                    print(f"[{scanned}] {action}")
                    if remove_item(page, article, target, args.pause):
                        removed += 1
                        print("  done")
                else:
                    print(f"[{scanned}] dry-run: would {dry_run_action}")
                time.sleep(args.pause)
                break

            try:
                text = post_text(article)
            except TimeoutError:
                break
            match = classify_post(text, keywords, hashtags)
            normalized_text = " ".join(text.split())
            preview = normalized_text[:180] + ("..." if len(normalized_text) > 180 else "")
            if not match.matched:
                print(f"[{scanned}] keep: {preview}")
                break

            print(f"[{scanned}] match: {preview}")
            print(f"  reasons: {', '.join(match.reasons)}")

            if args.delete:
                if remove_item(page, article, target, args.pause):
                    removed += 1
                    action = "unreposted" if target == Target.RETWEETS else "deleted"
                    print(f"  {action}")
            else:
                action = "unrepost" if target == Target.RETWEETS else "delete"
                print(f"  dry-run: would {action}")

            time.sleep(args.pause)
            break

        if limit_reached():
            break

        if processed_item:
            idle_scrolls = 0
            continue

        page.mouse.wheel(0, 1800)
        time.sleep(max(args.pause, 1.0))

        if made_progress:
            idle_scrolls = 0
        else:
            idle_scrolls += 1

        if idle_scrolls >= max_idle_scrolls:
            break

    return scanned, removed


def scan_targets(
    page: Page,
    args: argparse.Namespace,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    results: dict[Target, tuple[int, int]] = {}
    for target in targets:
        args.target = target.value
        target_label = "posts and replies" if args.delete_all and target == Target.REPLIES else target.value
        print(f"\nProcessing: {target_label}")
        open_profile(page, args.profile_url, target, allow_empty=len(targets) > 1)
        if page.locator("article").count() == 0:
            results[target] = (0, 0)
            print(f"No {target.value} timeline cards found; continuing.")
            continue
        results[target] = scan_and_maybe_delete(page, args, keywords, hashtags)
    return results


def run_browser(
    args: argparse.Namespace,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    if args.connect_cdp:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.connect_over_cdp(args.connect_cdp)
            except Exception as exc:
                raise RuntimeError(
                    "Could not connect to the existing browser over CDP. "
                    "Make sure Chrome/Chromium is still open and was started with both "
                    "--remote-debugging-port=9222 and a non-default --user-data-dir. "
                    "You can test it by opening http://127.0.0.1:9222/json/version."
                ) from exc
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            try:
                return scan_targets(page, args, keywords, hashtags, targets)
            finally:
                page.close()

    browser = BrowserName(args.browser)
    profile_dir = args.browser_profile_dir or default_profile_dir(browser)
    profile_dir.mkdir(exist_ok=True)
    launch_options = {
        "user_data_dir": str(profile_dir),
        "headless": args.headless,
        "viewport": {"width": 1365, "height": 900},
        "locale": "en-US",
    }
    if args.browser_channel:
        launch_options["channel"] = args.browser_channel
    if args.executable_path:
        launch_options["executable_path"] = str(args.executable_path)

    with sync_playwright() as playwright:
        try:
            context: BrowserContext = browser_type(playwright, browser).launch_persistent_context(**launch_options)
        except Exception as exc:
            if args.browser_profile_dir:
                raise RuntimeError(
                    "Could not open the browser profile. Close all browser windows using that profile, "
                    "or run without --browser-profile-dir and log in once through the Playwright browser window."
                ) from exc
            raise

        page = context.pages[0] if context.pages else context.new_page()
        try:
            login_if_requested(page, args.profile_url, args.login)
            return scan_targets(page, args, keywords, hashtags, targets)
        finally:
            context.close()


def main() -> int:
    try:
        args = apply_shortcuts(parse_args())
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.login and args.headless:
        print("--login requires a visible browser; remove --headless.", file=sys.stderr)
        return 2
    if args.connect_cdp and args.login:
        print("--connect-cdp uses an already-running browser; do not pass --login.", file=sys.stderr)
        return 2
    if args.connect_cdp and (args.browser_profile_dir or args.browser_channel or args.executable_path or args.headless):
        print(
            "--connect-cdp cannot be combined with --browser-profile-dir, --browser-channel, "
            "--executable-path, or --headless.",
            file=sys.stderr,
        )
        return 2
    if args.browser_channel and BrowserName(args.browser) != BrowserName.CHROMIUM:
        print("--browser-channel is only supported with --browser chromium.", file=sys.stderr)
        return 2
    if args.browser_channel and args.executable_path:
        print("Use either --browser-channel or --executable-path, not both.", file=sys.stderr)
        return 2

    if args.only_keywords_file and not args.keywords_file:
        print("--only-keywords-file requires --keywords-file", file=sys.stderr)
        return 2
    if args.max_posts is not None and args.max_posts < 1:
        print("--max-posts must be at least 1", file=sys.stderr)
        return 2

    keywords = load_keywords(args.keywords_file, args.only_keywords_file)
    hashtags = set() if args.only_keywords_file else set(DEFAULT_POLITICAL_HASHTAGS)
    if MatchMode(args.match) == MatchMode.POLITICS and not keywords:
        print("No political keywords configured.", file=sys.stderr)
        return 2

    mode = "DELETE" if args.delete else "DRY RUN"
    print(f"Mode: {mode}")
    if args.connect_cdp:
        print(f"Browser: existing Chrome/Chromium via CDP at {args.connect_cdp}")
    else:
        print(f"Browser: {args.browser}")
        if args.browser_channel:
            print(f"Browser channel: {args.browser_channel}")
        if args.executable_path:
            print(f"Executable: {args.executable_path}")
        print(f"Profile: {args.browser_profile_dir or default_profile_dir(BrowserName(args.browser))}")
    # The with_replies timeline contains both original posts and replies. Using
    # it first avoids a full Posts-only scroll before combined deletion starts.
    targets = [Target.REPLIES, Target.RETWEETS] if args.delete_all else [Target(args.target)]
    print(f"Target: {'posts, replies, retweets' if args.delete_all else args.target}")
    print(f"Match: {args.match}")
    print(f"Scan limit: {args.max_posts if args.max_posts is not None else 'entire timeline'}")
    if MatchMode(args.match) == MatchMode.POLITICS:
        print(f"Keywords loaded: {len(keywords)}")
    print("Use Ctrl+C to stop at any time.")

    try:
        results = run_browser(args, keywords, hashtags, targets)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    total_scanned = 0
    total_removed = 0
    for target in targets:
        scanned, removed = results[target]
        total_scanned += scanned
        total_removed += removed
        action = "unreposted" if target == Target.RETWEETS else "deleted"
        target_label = "posts and replies" if args.delete_all and target == Target.REPLIES else target.value
        print(f"Done: scanned {scanned} {target_label}; {action} {removed}.")
    if len(targets) > 1:
        print(f"Total: scanned {total_scanned}; removed {total_removed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
