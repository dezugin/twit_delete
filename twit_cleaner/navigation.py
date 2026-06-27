from __future__ import annotations

import re
import time

from playwright.sync_api import Page

from .models import Target
from .urls import origin_from_url, timeline_url


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
    if page.locator("article").count() > 0 or allow_empty:
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

