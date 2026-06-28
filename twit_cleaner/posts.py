from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError, Locator, TimeoutError

from .models import PostKind, Target
from .urls import canonical_owned_status_url


REPOST_MARKERS = (
    "reposted",
    "repostou",
    "retweeted",
    "retweetou",
    "you reposted",
    "voce repostou",
    "você repostou",
)
OWN_REPOST_MARKERS = (
    "you reposted",
    "you retweeted",
    "voce repostou",
    "você repostou",
    "voce retweetou",
    "você retweetou",
)


def post_text(article: Locator) -> str:
    try:
        text_nodes = article.locator('[data-testid="tweetText"]')
        if text_nodes.count():
            return "\n".join(
                text_nodes.nth(index).inner_text(timeout=1500) for index in range(text_nodes.count())
            )
    except TimeoutError:
        pass
    return article.inner_text(timeout=2000)


def post_fingerprint(article: Locator) -> str:
    status_links = article.locator('a[href*="/status/"]')
    for index in range(status_links.count()):
        href = status_links.nth(index).get_attribute("href")
        if href and "/status/" in href:
            return href.split("?")[0]
    return " ".join(article.inner_text(timeout=2000).split())


def owned_status_url(article: Locator, profile_url: str) -> str | None:
    timestamp_links = article.locator('a:has(time)[href*="/status/"]')
    if timestamp_links.count() == 0:
        return None
    return canonical_owned_status_url(timestamp_links.first.get_attribute("href"), profile_url)


def active_unretweet_button(article: Locator) -> Locator | None:
    buttons = article.locator('[data-testid="unretweet"]')
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if button.is_visible(timeout=400) and button.is_enabled(timeout=400):
                return button
        except PlaywrightError:
            continue
    return None


def available_repost_button(article: Locator) -> Locator | None:
    buttons = article.locator('[data-testid="retweet"]')
    for index in range(buttons.count()):
        button = buttons.nth(index)
        try:
            if button.is_visible(timeout=400) and button.is_enabled(timeout=400):
                return button
        except PlaywrightError:
            continue
    return None


def text_has_repost_marker(text: str) -> bool:
    return any(marker in text.lower() for marker in REPOST_MARKERS)


def text_has_own_repost_marker(text: str) -> bool:
    return any(marker in text.lower() for marker in OWN_REPOST_MARKERS)


def repost_social_context(article: Locator) -> str:
    social_contexts = article.locator('[data-testid="socialContext"]')
    return " ".join(
        social_contexts.nth(index).inner_text(timeout=800)
        for index in range(social_contexts.count())
    )


def has_repost_marker(article: Locator) -> bool:
    try:
        return text_has_repost_marker(repost_social_context(article))
    except PlaywrightError:
        return False


def has_own_repost_marker(article: Locator) -> bool:
    try:
        return text_has_own_repost_marker(repost_social_context(article))
    except PlaywrightError:
        return False


def combined_action_target(
    has_active_unretweet: bool,
    status_url: str | None,
    has_stale_repost_marker: bool = False,
) -> Target | None:
    if has_active_unretweet or has_stale_repost_marker:
        return Target.RETWEETS
    if status_url:
        return Target.POSTS
    return None


def exclusions_apply(target: Target, exclusion_mode: str | None) -> bool:
    return bool(exclusion_mode) and target != Target.RETWEETS


def post_kind(article: Locator) -> PostKind:
    text = " ".join(article.inner_text(timeout=2000).split()).lower()
    is_reply = any(marker in text for marker in ("replying to", "em resposta a", "respondendo a"))
    is_retweet = active_unretweet_button(article) is not None or has_repost_marker(article)
    return PostKind(is_reply=is_reply, is_retweet=is_retweet)


def matches_target(kind: PostKind, target: Target) -> bool:
    if target == Target.RETWEETS:
        return kind.is_retweet
    if target == Target.REPLIES:
        return not kind.is_retweet
    return not kind.is_reply and not kind.is_retweet
