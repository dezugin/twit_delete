from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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


class ExclusionMode(str, Enum):
    PERSONAL = "personal"
    WORK = "work"
    CUSTOM = "custom"


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PostKind:
    is_reply: bool
    is_retweet: bool


@dataclass(frozen=True)
class KeywordRules:
    political_keywords: frozenset[str]
    political_hashtags: frozenset[str]
    exclusion_keywords: frozenset[str]
    exclusion_hashtags: frozenset[str]


@dataclass(frozen=True)
class ScanOptions:
    profile_url: str
    target: Target
    match_mode: MatchMode
    max_posts: int | None
    delete: bool
    delete_all: bool
    pause: float
    exclusion_mode: str | None
    exclusion_keywords: frozenset[str]
    exclusion_hashtags: frozenset[str]


@dataclass(frozen=True)
class BrowserOptions:
    browser: BrowserName
    profile_dir: Path | None
    channel: str | None
    executable_path: Path | None
    connect_cdp: str | None
    login: bool
    headless: bool
