from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .models import Target


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
    return urlunsplit((parsed.scheme or "https", parsed.netloc or "x.com", "", "", ""))


def profile_handle(profile_url: str) -> str:
    parts = [part for part in urlsplit(profile_url).path.split("/") if part]
    return parts[0].lower() if parts else ""


def canonical_owned_status_url(href: str | None, profile_url: str) -> str | None:
    if not href:
        return None
    parts = [part for part in urlsplit(href).path.split("/") if part]
    if (
        len(parts) < 3
        or parts[0].lower() != profile_handle(profile_url)
        or parts[1] != "status"
        or not parts[2].isdigit()
    ):
        return None
    return f"{origin_from_url(profile_url)}/{parts[0]}/status/{parts[2]}"

