from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .models import KeywordRules, MatchMode, MatchResult


def configured_terms(data: object, section: str, key: str, hashtags: bool = False) -> frozenset[str]:
    if not isinstance(data, dict) or not isinstance(data.get(section), dict):
        raise ValueError(f"Keyword profiles must contain an object named '{section}'.")
    values = data[section].get(key)
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError(f"Keyword profile '{section}.{key}' must be a list of strings.")
    return frozenset(
        value.strip().lower().removeprefix("#") if hashtags else value.strip().lower()
        for value in values
        if value.strip()
    )


def load_custom_terms(path: Path | None) -> tuple[frozenset[str], frozenset[str]]:
    if not path:
        return frozenset(), frozenset()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ValueError(f"Custom keywords file not found: {path}") from exc

    terms = [
        term.lower()
        for line in lines
        if not line.lstrip().startswith("//")
        for term in line.split()
        if term
    ]
    return partition_terms(terms)


def partition_terms(terms: Iterable[str]) -> tuple[frozenset[str], frozenset[str]]:
    normalized = [term.strip().lower() for term in terms if term.strip()]
    return (
        frozenset(term for term in normalized if not term.startswith("#")),
        frozenset(
            term.removeprefix("#")
            for term in normalized
            if term.startswith("#") and len(term) > 1
        ),
    )


def profile_terms(data: object, profile: str) -> tuple[frozenset[str], frozenset[str]]:
    if profile == MatchMode.CUSTOM.value:
        return frozenset(), frozenset()
    return (
        configured_terms(data, profile, "keywords"),
        configured_terms(data, profile, "hashtags", hashtags=True),
    )


def load_keyword_rules(
    path: Path,
    match_mode: str,
    exclusion_mode: str | None,
    match_file: Path | None = None,
    exclusion_file: Path | None = None,
    inline_match_terms: Iterable[str] = (),
    inline_exclusion_terms: Iterable[str] = (),
) -> KeywordRules:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Keyword profiles file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Keyword profiles file is invalid JSON: {path}: {exc}") from exc

    match_keywords: frozenset[str] = frozenset()
    match_hashtags: frozenset[str] = frozenset()
    if match_mode != MatchMode.ALL.value:
        match_keywords, match_hashtags = profile_terms(data, match_mode)
    custom_match_keywords, custom_match_hashtags = load_custom_terms(match_file)
    inline_match_keywords, inline_match_hashtags = partition_terms(inline_match_terms)
    match_keywords |= custom_match_keywords
    match_hashtags |= custom_match_hashtags
    match_keywords |= inline_match_keywords
    match_hashtags |= inline_match_hashtags

    exclusion_keywords = frozenset()
    exclusion_hashtags = frozenset()
    if exclusion_mode:
        exclusion_keywords, exclusion_hashtags = profile_terms(data, exclusion_mode)
    custom_exclusion_keywords, custom_exclusion_hashtags = load_custom_terms(exclusion_file)
    inline_exclusion_keywords, inline_exclusion_hashtags = partition_terms(inline_exclusion_terms)
    exclusion_keywords |= custom_exclusion_keywords
    exclusion_hashtags |= custom_exclusion_hashtags
    exclusion_keywords |= inline_exclusion_keywords
    exclusion_hashtags |= inline_exclusion_hashtags

    return KeywordRules(
        match_keywords=match_keywords,
        match_hashtags=match_hashtags,
        exclusion_keywords=exclusion_keywords,
        exclusion_hashtags=exclusion_hashtags,
    )


def keyword_regex(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword)
    if re.match(r"^[\w -]+$", keyword, flags=re.IGNORECASE):
        escaped = escaped.replace(r"\ ", r"\s+")
        return re.compile(rf"(?<!\w){escaped}(?!\w)", flags=re.IGNORECASE)
    return re.compile(escaped, flags=re.IGNORECASE)


def classify_post(text: str, keywords: Iterable[str], hashtags: set[str]) -> MatchResult:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    reasons = [f"hashtag #{tag}" for tag in re.findall(r"#([\w_]+)", lowered) if tag in hashtags]
    reasons.extend(
        f"keyword '{keyword}'" for keyword in sorted(keywords) if keyword_regex(keyword).search(normalized)
    )
    return MatchResult(bool(reasons), tuple(reasons[:8]))
