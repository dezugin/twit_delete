from __future__ import annotations

import re
import time
from typing import Iterable
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError, Locator, Page, TimeoutError

from .constants import CONFIRM_DELETE_LABELS, DELETE_LABELS, MENU_LABELS, UNREPOST_LABELS
from .models import Target
from .posts import active_unretweet_button


def first_visible_by_labels(
    scope: Page | Locator,
    role: str,
    labels: Iterable[str],
    timeout: int = 600,
) -> Locator | None:
    for label in labels:
        try:
            locator = scope.get_by_role(role, name=re.compile(rf"^{re.escape(label)}$", re.IGNORECASE))
            if locator.first.is_visible(timeout=timeout):
                return locator.first
        except TimeoutError:
            continue
    return None


def delete_post(page: Page, article: Locator, pause: float) -> bool:
    menu_button = first_visible_by_labels(article, "button", MENU_LABELS)
    if not menu_button:
        testid_menu = article.locator('[data-testid="caret"]').first
        try:
            if testid_menu.is_visible(timeout=1200):
                menu_button = testid_menu
        except PlaywrightError:
            pass
    if not menu_button:
        print("  skip: post menu not found")
        return False

    try:
        menu_button.click(timeout=3000)
    except PlaywrightError:
        print("  skip: post menu could not be clicked")
        return False
    time.sleep(pause)

    delete_item = first_visible_by_labels(page, "menuitem", DELETE_LABELS, timeout=1200)
    if not delete_item:
        delete_item = first_visible_by_labels(page, "button", DELETE_LABELS, timeout=1200)
    if not delete_item:
        page.keyboard.press("Escape")
        print("  skip: delete action not found")
        return False

    try:
        delete_item.click(timeout=3000)
    except PlaywrightError:
        page.keyboard.press("Escape")
        print("  skip: delete action could not be clicked")
        return False
    time.sleep(pause)

    confirm_button = first_visible_by_labels(page, "button", CONFIRM_DELETE_LABELS, timeout=2500)
    if not confirm_button:
        testid_confirm = page.locator('[data-testid="confirmationSheetConfirm"]').first
        try:
            if testid_confirm.is_visible(timeout=1200):
                confirm_button = testid_confirm
        except PlaywrightError:
            pass
    if not confirm_button:
        page.keyboard.press("Escape")
        print("  skip: confirmation button not found")
        return False

    try:
        confirm_button.click(timeout=3000)
    except PlaywrightError:
        page.keyboard.press("Escape")
        print("  skip: confirmation button could not be clicked")
        return False
    time.sleep(pause)
    return True


def article_for_status(page: Page, status_url: str) -> Locator | None:
    target_path = urlsplit(status_url).path.rstrip("/")
    articles = page.locator("article")
    for article_index in range(articles.count()):
        article = articles.nth(article_index)
        links = article.locator('a[href*="/status/"]')
        for link_index in range(links.count()):
            href = links.nth(link_index).get_attribute("href")
            if href and urlsplit(href).path.rstrip("/") == target_path:
                return article
    return None


def delete_post_at_permalink(page: Page, status_url: str, pause: float) -> bool:
    detail_page = page.context.new_page()
    try:
        print(f"  fallback: opening {status_url}")
        detail_page.goto(status_url, wait_until="domcontentloaded", timeout=60_000)
        detail_page.locator("article").first.wait_for(state="visible", timeout=15_000)
        article = article_for_status(detail_page, status_url)
        if not article:
            print("  skip: owned post was not found on its permalink page")
            return False
        if delete_post(detail_page, article, pause):
            print("  fallback: deleted from permalink page")
            return True
        print("  skip: permalink deletion also failed")
        return False
    except PlaywrightError:
        print("  skip: permalink page could not be loaded or became stale")
        return False
    finally:
        try:
            detail_page.close()
        except PlaywrightError:
            pass


def undo_retweet(page: Page, article: Locator, pause: float) -> bool:
    repost_button = active_unretweet_button(article)
    if not repost_button:
        print("  skip: active Undo repost control not found")
        return False
    try:
        repost_button.click(timeout=3000)
    except PlaywrightError:
        print("  skip: active Undo repost control was unavailable or became stale")
        return False
    time.sleep(pause)

    undo_item = first_visible_by_labels(page, "menuitem", UNREPOST_LABELS, timeout=1800)
    if not undo_item:
        undo_item = first_visible_by_labels(page, "button", UNREPOST_LABELS, timeout=1800)
    if not undo_item:
        page.keyboard.press("Escape")
        print("  skip: undo repost action not found")
        return False
    try:
        undo_item.click(timeout=3000)
    except PlaywrightError:
        page.keyboard.press("Escape")
        print("  skip: Undo repost action could not be clicked")
        return False
    time.sleep(pause)
    return True


def remove_item(
    page: Page,
    article: Locator,
    target: Target,
    pause: float,
    status_url: str | None = None,
) -> bool:
    if active_unretweet_button(article):
        print("  checked: repost; using Undo repost")
        return undo_retweet(page, article, pause)
    if target == Target.RETWEETS:
        print("  skip: item has no active Undo repost control")
        return False

    print("  checked: not a repost; using Delete")
    if delete_post(page, article, pause):
        return True
    if status_url:
        return delete_post_at_permalink(page, status_url, pause)
    print("  skip: no owned permalink was available for fallback")
    return False

