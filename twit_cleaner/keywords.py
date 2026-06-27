from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .models import KeywordRules, MatchResult


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


def load_keyword_rules(path: Path, exclusion_mode: str | None) -> KeywordRules:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Keyword profiles file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Keyword profiles file is invalid JSON: {path}: {exc}") from exc

    exclusion_keywords: frozenset[str] = frozenset()
    exclusion_hashtags: frozenset[str] = frozenset()
    if exclusion_mode:
        exclusions = data.get("exclusions") if isinstance(data, dict) else None
        exclusion_keywords = configured_terms(exclusions, exclusion_mode, "keywords")
        exclusion_hashtags = configured_terms(exclusions, exclusion_mode, "hashtags", hashtags=True)

    return KeywordRules(
        political_keywords=configured_terms(data, "politics", "keywords"),
        political_hashtags=configured_terms(data, "politics", "hashtags", hashtags=True),
        exclusion_keywords=exclusion_keywords,
        exclusion_hashtags=exclusion_hashtags,
    )


def load_keyword_file(path: Path | None) -> set[str]:
    if not path:
        return set()
    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


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

