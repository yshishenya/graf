from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from ipaddress import ip_address
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s<>'\"]+")


@dataclass(frozen=True, slots=True)
class ClassifiedConferenceLink:
    provider_family: str
    url_hash: str
    redacted_url_preview: str
    contains_passcode: bool
    open_url: str


PROVIDER_HOSTS = (
    ("meet.google.com", "google_meet"),
    ("teams.microsoft.com", "microsoft_teams"),
    ("teams.live.com", "microsoft_teams"),
    ("telemost.yandex.ru", "yandex_telemost"),
    ("telemost.yandex.com", "yandex_telemost"),
    ("mts-link.ru", "mts_link"),
    ("webinar.ru", "mts_link"),
    ("talk.kontur.ru", "kontur_talk"),
    ("trueconf.ru", "trueconf"),
    ("trueconf.com", "trueconf"),
    ("calls.vk.com", "vk_calls"),
    ("zoom.us", "zoom"),
    ("zoom.com", "zoom"),
    ("webex.com", "webex"),
)


def classify_conference_link(url: str) -> ClassifiedConferenceLink:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    provider = next(
        (
            family
            for domain, family in PROVIDER_HOSTS
            if host == domain or host.endswith("." + domain)
        ),
        "generic",
    )
    return ClassifiedConferenceLink(
        provider_family=provider,
        url_hash=f"sha256:{sha256(url.encode('utf-8')).hexdigest()}",
        redacted_url_preview=safe_link_preview(url),
        contains_passcode="passcode" in url.lower() or "pwd=" in url.lower(),
        open_url=url,
    )


def safe_open_meeting_url(value: str | None) -> str | None:
    url = (value or "").strip()
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        _port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        return None
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return None
    try:
        if not ip_address(hostname).is_global:
            return None
    except ValueError:
        pass
    return url


def safe_link_preview(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return f"{host}/..." if host else "unknown/..."


def extract_conference_link_candidates(*texts: str | None) -> list[ClassifiedConferenceLink]:
    seen: set[str] = set()
    candidates: list[ClassifiedConferenceLink] = []
    for text in texts:
        if not text:
            continue
        for raw_url in URL_RE.findall(unescape(text)):
            url = raw_url.rstrip(").,;")
            if safe_open_meeting_url(url) is None:
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append(classify_conference_link(url))
    return candidates


def conference_link_dicts(*fields: tuple[str, str | None]) -> list[dict]:
    """Use one URL policy and prefer recognizable call links over agenda links."""
    links: dict[str, dict] = {}
    for source_field, text in fields:
        for candidate in extract_conference_link_candidates(text):
            if safe_open_meeting_url(candidate.open_url) is None:
                continue
            links.setdefault(
                candidate.url_hash,
                {
                    "provider_family": candidate.provider_family,
                    "source_field": source_field,
                    "url_hash": candidate.url_hash,
                    "redacted_url_preview": candidate.redacted_url_preview,
                    "contains_passcode": candidate.contains_passcode,
                    "sensitivity_class": "meeting_link",
                    "open_url": candidate.open_url,
                },
            )
    return sorted(links.values(), key=lambda link: link["provider_family"] == "generic")
