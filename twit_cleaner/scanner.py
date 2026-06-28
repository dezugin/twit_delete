from __future__ import annotations

import time
from dataclasses import replace

from playwright.sync_api import Error as PlaywrightError, Page

from .actions import remove_item
from .keywords import classify_post
from .models import MatchMode, ScanOptions, Target
from .navigation import open_profile
from .posts import (
    active_unretweet_button,
    combined_action_target,
    exclusions_apply,
    has_own_repost_marker,
    matches_target,
    owned_status_url,
    post_fingerprint,
    post_kind,
    post_text,
)


def scan_and_maybe_delete(
    page: Page,
    options: ScanOptions,
    keywords: set[str],
    hashtags: set[str],
) -> tuple[int, int]:
    scanned = 0
    removed = 0
    seen_cards: set[str] = set()
    idle_scrolls = 0

    def limit_reached() -> bool:
        return options.max_posts is not None and scanned >= options.max_posts

    while not limit_reached():
        articles = page.locator("article")
        made_progress = False
        processed_item = False

        for index in range(articles.count()):
            if limit_reached():
                break
            article = articles.nth(index)
            try:
                status_url = owned_status_url(article, options.profile_url)
                fingerprint = status_url or post_fingerprint(article)
            except PlaywrightError:
                continue
            if not fingerprint or fingerprint in seen_cards:
                continue

            seen_cards.add(fingerprint)
            made_progress = True
            action_target = options.target
            content_text: str | None = None

            if options.delete_all:
                action_target = combined_action_target(
                    active_unretweet_button(article) is not None,
                    status_url,
                    has_own_repost_marker(article),
                )
                if not action_target:
                    continue
            else:
                try:
                    kind = post_kind(article)
                except PlaywrightError:
                    continue
                if not matches_target(kind, options.target):
                    continue

            if exclusions_apply(action_target, options.exclusion_mode):
                try:
                    content_text = post_text(article)
                except PlaywrightError:
                    continue
                exclusion = classify_post(
                    content_text,
                    set(options.exclusion_keywords),
                    set(options.exclusion_hashtags),
                )
                if exclusion.matched:
                    scanned += 1
                    processed_item = True
                    preview = " ".join(content_text.split())[:180]
                    print(f"[{scanned}] excluded by {options.exclusion_mode}: {preview}")
                    print(f"  reasons: {', '.join(exclusion.reasons)}")
                    break

            scanned += 1
            processed_item = True
            stale_repost = (
                action_target == Target.RETWEETS
                and active_unretweet_button(article) is None
                and has_own_repost_marker(article)
            )
            if options.match_mode == MatchMode.ALL:
                if stale_repost:
                    dry_run_action = "repost, then undo repost"
                else:
                    dry_run_action = "undo repost" if action_target == Target.RETWEETS else "delete"
                if options.delete:
                    print(f"[{scanned}] checking item type before removal")
                    if status_url:
                        print(f"  owned: {status_url}")
                    if remove_item(page, article, action_target, options.pause, status_url):
                        removed += 1
                        print("  done")
                        if action_target == Target.RETWEETS and status_url:
                            seen_cards.discard(fingerprint)
                else:
                    print(f"[{scanned}] dry-run: would {dry_run_action}")
                time.sleep(options.pause)
                break

            if content_text is None:
                try:
                    content_text = post_text(article)
                except PlaywrightError:
                    break
            match = classify_post(content_text, keywords, hashtags)
            normalized_text = " ".join(content_text.split())
            preview = normalized_text[:180] + ("..." if len(normalized_text) > 180 else "")
            if not match.matched:
                print(f"[{scanned}] keep: {preview}")
                break

            print(f"[{scanned}] match: {preview}")
            print(f"  reasons: {', '.join(match.reasons)}")
            if options.delete:
                if remove_item(page, article, action_target, options.pause, status_url):
                    removed += 1
                    action = "reposted and unreposted" if stale_repost else "unreposted"
                    if action_target != Target.RETWEETS:
                        action = "deleted"
                    print(f"  {action}")
            else:
                if stale_repost:
                    action = "repost, then undo repost"
                else:
                    action = "unrepost" if action_target == Target.RETWEETS else "delete"
                print(f"  dry-run: would {action}")
            time.sleep(options.pause)
            break

        if limit_reached():
            break
        if processed_item:
            idle_scrolls = 0
            continue

        page.mouse.wheel(0, 1800)
        time.sleep(max(options.pause, 1.0))
        idle_scrolls = 0 if made_progress else idle_scrolls + 1
        if idle_scrolls >= 5:
            break

    return scanned, removed


def scan_targets(
    page: Page,
    options: ScanOptions,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    results: dict[Target, tuple[int, int]] = {}
    for target in targets:
        target_options = replace(options, target=target)
        target_label = "reposts and owned posts/replies" if options.delete_all else target.value
        print(f"\nProcessing: {target_label}")
        navigation_target = Target.REPLIES if options.delete_all else target
        open_profile(
            page,
            options.profile_url,
            navigation_target,
            allow_empty=options.delete_all or len(targets) > 1,
        )
        if page.locator("article").count() == 0:
            results[target] = (0, 0)
            print(f"No {target_label} timeline cards found; continuing.")
            continue
        results[target] = scan_and_maybe_delete(page, target_options, keywords, hashtags)
    return results
