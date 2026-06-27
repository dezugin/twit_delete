from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright

from .models import BrowserName, BrowserOptions, ScanOptions, Target
from .navigation import login_if_requested
from .scanner import scan_targets


def default_profile_dir(browser: BrowserName) -> Path:
    if browser == BrowserName.FIREFOX:
        return Path(".browser-profile-firefox")
    return Path(".browser-profile")


def browser_type(playwright, browser: BrowserName):
    if browser == BrowserName.FIREFOX:
        return playwright.firefox
    return playwright.chromium


def run_browser(
    browser_options: BrowserOptions,
    scan_options: ScanOptions,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    if browser_options.connect_cdp:
        return run_attached_browser(browser_options, scan_options, keywords, hashtags, targets)
    return run_persistent_browser(browser_options, scan_options, keywords, hashtags, targets)


def run_attached_browser(
    browser_options: BrowserOptions,
    scan_options: ScanOptions,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(browser_options.connect_cdp)
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
            return scan_targets(page, scan_options, keywords, hashtags, targets)
        finally:
            page.close()


def run_persistent_browser(
    browser_options: BrowserOptions,
    scan_options: ScanOptions,
    keywords: set[str],
    hashtags: set[str],
    targets: list[Target],
) -> dict[Target, tuple[int, int]]:
    profile_dir = browser_options.profile_dir or default_profile_dir(browser_options.browser)
    profile_dir.mkdir(exist_ok=True)
    launch_options: dict[str, object] = {
        "user_data_dir": str(profile_dir),
        "headless": browser_options.headless,
        "viewport": {"width": 1365, "height": 900},
        "locale": "en-US",
    }
    if browser_options.channel:
        launch_options["channel"] = browser_options.channel
    if browser_options.executable_path:
        launch_options["executable_path"] = str(browser_options.executable_path)

    with sync_playwright() as playwright:
        try:
            context: BrowserContext = browser_type(playwright, browser_options.browser).launch_persistent_context(
                **launch_options
            )
        except Exception as exc:
            if browser_options.profile_dir:
                raise RuntimeError(
                    "Could not open the browser profile. Close all browser windows using that profile, "
                    "or run without --browser-profile-dir and log in once through the Playwright browser window."
                ) from exc
            raise

        page = context.pages[0] if context.pages else context.new_page()
        try:
            login_if_requested(page, scan_options.profile_url, browser_options.login)
            return scan_targets(page, scan_options, keywords, hashtags, targets)
        finally:
            context.close()

