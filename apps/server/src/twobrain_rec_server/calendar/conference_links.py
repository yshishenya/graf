from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
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


PROVIDER_HOST_MARKERS = (
    ("telemost.yandex.", "yandex_telemost"),
    ("mts-link.ru", "mts_link"),
    ("talk.kontur", "kontur_talk"),
    ("trueconf", "trueconf"),
    ("calls.vk.", "vk_calls"),
    ("zoom.", "zoom"),
    ("webex.", "webex"),
)


def classify_conference_link(url: str) -> ClassifiedConferenceLink:
    host = urlparse(url).netloc.lower()
    provider = next((family for marker, family in PROVIDER_HOST_MARKERS if marker in host), "generic")
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
        for raw_url in URL_RE.findall(text):
            url = raw_url.rstrip(").,;")
            if url in seen:
                continue
            seen.add(url)
            candidates.append(classify_conference_link(url))
    return candidates
