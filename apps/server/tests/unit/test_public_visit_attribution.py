"""Level 2 and level 3 rules of the public pages (T029, T030, T031).

The visit attribution lives in a session cookie, not in a tracking identifier:
these tests read the cookie the code actually writes, move it between public
pages the way a browser would, and prove that campaign labels survive the move
while nothing that could identify a visitor is stored.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ANONYMOUS_AGGREGATE_ALLOWED_FIELDS,
)
from twobrain_rec_server.public.analytics import (
    PUBLIC_VISIT_ATTRIBUTION_COOKIE,
    PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
    PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES,
    PUBLIC_VISIT_ATTRIBUTION_MAX_REFS,
    PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS,
    PUBLIC_VISIT_ATTRIBUTION_VERSION,
    PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD,
    apply_public_visit_attribution_cookie,
    build_public_consent_share_report,
    build_public_page_aggregate_bucket,
    read_public_visit_attribution,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
BROWSER_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"


class _FakeRequest:
    """The smallest request shape the public analytics helpers read."""

    def __init__(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        client_host: str = "203.0.113.10",
        scheme: str = "https",
    ) -> None:
        self.url = SimpleNamespace(path=path, scheme=scheme)
        self.query_params = dict(query or {})
        self.cookies = dict(cookies or {})
        self.headers = {"user-agent": BROWSER_USER_AGENT, **(headers or {})}
        self.client = SimpleNamespace(host=client_host)
        self.app = SimpleNamespace(state=SimpleNamespace(settings=Settings()))


class _FakeResponse:
    def __init__(self) -> None:
        self.cookies: list[tuple[str, str, dict[str, Any]]] = []

    def set_cookie(self, key: str, value: str, **options: Any) -> None:
        self.cookies.append((key, value, options))


def _visit(
    path: str,
    *,
    query: dict[str, str] | None = None,
    cookie: tuple[str, str] | None = None,
) -> tuple[dict[str, str | None], tuple[str, str, dict[str, Any]] | None]:
    """Walk one public page like a browser: read, then write back the cookie."""
    cookies = {cookie[0]: cookie[1]} if cookie else {}
    request = _FakeRequest(path, query=query, cookies=cookies)
    attribution = read_public_visit_attribution(request, now=NOW)
    response = _FakeResponse()
    apply_public_visit_attribution_cookie(response, request, attribution=attribution)
    written = response.cookies[0] if response.cookies else None
    return attribution, written


def _labels(attribution: dict[str, str | None]) -> dict[str, str | None]:
    return {field: attribution[field] for field in PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS}


def test_visit_attribution_documents_its_cookie_and_returned_shape() -> None:
    docstring = read_public_visit_attribution.__doc__ or ""

    assert PUBLIC_VISIT_ATTRIBUTION_COOKIE in docstring
    for field in (
        *PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
        PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD,
        *PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS,
        "attribution_status",
    ):
        assert field in docstring
    first, written = _visit("/", query={"utm_source": "yandex_direct"})
    assert set(first) == {
        *PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
        PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD,
        *PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS,
        "attribution_ref",
        "attribution_refs",
        "attribution_status",
    }
    assert written is not None


def test_campaign_labels_survive_public_page_transitions_in_a_session_cookie() -> None:
    landing, cookie = _visit(
        "/",
        query={
            "utm_source": "Yandex_Direct",
            "utm_medium": "CPC",
            "utm_campaign": "launch",
            "utm_id": "42",
            "utm_content": "ad-a",
            "utm_term": "meeting-notes",
        },
    )

    assert cookie is not None
    name, value, options = cookie
    assert name == PUBLIC_VISIT_ATTRIBUTION_COOKIE
    # A session cookie: no Max-Age and no Expires, so it cannot follow a visitor
    # into a later visit (FR-014).
    assert "max_age" not in options and "expires" not in options
    assert options["path"] == "/"
    assert options["httponly"] is True
    assert options["samesite"] == "lax"
    assert options["secure"] is True
    assert len(value) <= PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES

    stored = json.loads(value)
    assert stored["v"] == PUBLIC_VISIT_ATTRIBUTION_VERSION
    assert set(stored) == {
        "v",
        *PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
        *PUBLIC_VISIT_ATTRIBUTION_STATUS_FIELDS,
        "attribution_ref",
        "attribution_refs",
    }
    assert stored["attribution_ref"].startswith("graf_visit_")
    assert stored["attribution_refs"] == [stored["attribution_ref"]]
    for identifier_field in ("visit_id", "session_id", "client_id", "distinct_id"):
        assert identifier_field not in stored
    assert landing["landing_path"] == "/"
    assert _labels(landing)["utm_source"] == "yandex_direct"
    assert _labels(landing)["utm_medium"] == "cpc"
    assert landing["attribution_status"] == "current"
    assert landing["first_seen_at"] == NOW.isoformat()

    download, second_cookie = _visit("/download", cookie=cookie)
    assert _labels(download) == _labels(landing)
    assert download["landing_path"] == "/"
    assert download["attribution_status"] == "saved"
    assert second_cookie is not None

    privacy, _ = _visit("/privacy", cookie=second_cookie and (second_cookie[0], second_cookie[1]))
    consent_page, _ = _visit("/analytics-consent", cookie=cookie)
    for attribution in (privacy, consent_page):
        assert _labels(attribution) == _labels(landing)
        assert attribution["landing_path"] == "/"
        assert attribution["attribution_status"] == "saved"


def test_visit_attribution_ring_is_bounded_deduplicated_and_newest_first() -> None:
    cookie = None
    refs = []
    for index in range(10):
        _, cookie = _visit(
            "/download",
            query={"utm_source": "yandex_direct", "utm_campaign": f"campaign-{index}"},
            cookie=cookie,
        )
        assert cookie is not None
        payload = json.loads(cookie[1])
        refs.append(payload["attribution_ref"])
        assert len(payload["attribution_refs"]) <= PUBLIC_VISIT_ATTRIBUTION_MAX_REFS
        assert payload["attribution_refs"][0] == payload["attribution_ref"]
        assert len(payload["attribution_refs"]) == len(set(payload["attribution_refs"]))
    assert json.loads(cookie[1])["attribution_refs"] == refs[-PUBLIC_VISIT_ATTRIBUTION_MAX_REFS :][::-1]


def test_old_v1_cookie_is_read_with_a_compatibility_current_reference() -> None:
    old_ref = "graf_visit_0123456789abcdef"
    payload = {
        "v": 1,
        "utm_source": "yandex_direct",
        "utm_campaign": "old-campaign",
        "landing_path": "/download",
        "first_seen_at": NOW.isoformat(),
        "attribution_ref": old_ref,
    }
    attribution = read_public_visit_attribution(
        _FakeRequest("/download", cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: json.dumps(payload)}),
        now=NOW,
    )
    assert attribution["attribution_ref"] == old_ref
    assert list(attribution["attribution_refs"]) == [old_ref]
    assert attribution["attribution_status"] == "saved"


def test_visit_attribution_keeps_the_last_non_direct_source_of_the_visit() -> None:
    _, cookie = _visit("/", query={"utm_source": "yandex_direct", "utm_campaign": "launch"})

    moved, moved_cookie = _visit(
        "/download",
        query={"utm_source": "google", "utm_medium": "cpc"},
        cookie=(cookie[0], cookie[1]),
    )

    assert _labels(moved)["utm_source"] == "google"
    assert _labels(moved)["utm_medium"] == "cpc"
    # The campaign of the second click replaces the first, while the landing page
    # of the visit stays the page the visit started from.
    assert _labels(moved)["utm_campaign"] is None
    assert moved["landing_path"] == "/"
    assert moved["referrer_category"] == "paid"
    assert moved["attribution_status"] == "current"
    assert moved_cookie is not None
    assert json.loads(moved_cookie[1])["attribution_ref"] != json.loads(cookie[1])["attribution_ref"]


def test_a_visit_without_campaign_material_gets_no_cookie_at_all() -> None:
    attribution, cookie = _visit("/privacy")

    assert cookie is None
    assert _labels(attribution) == dict.fromkeys(PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS)
    assert attribution["attribution_status"] == "missing"
    assert attribution[PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD] is None
    # The landing page is known even without a campaign: it is the page the
    # visitor is on. The registration path needs it, because the client
    # acquisition attribute and the level 1 bucket both require a landing path.
    assert attribution["landing_path"] == "/privacy"


def test_yandex_click_identifier_is_kept_with_the_visit_and_nothing_else() -> None:
    landing, cookie = _visit("/", query={"yclid": "9876543210abcdef"})
    assert cookie is not None
    assert landing[PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD] == "9876543210abcdef"
    assert landing["attribution_status"] == "current"

    download, _ = _visit("/download", cookie=(cookie[0], cookie[1]))
    assert download[PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD] == "9876543210abcdef"

    # A malformed value is dropped instead of being remembered.
    broken, broken_cookie = _visit("/", query={"yclid": "short"})
    assert broken[PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD] is None
    assert broken_cookie is None

    # The click identifier never reaches the level 1 aggregate: its allowlist has
    # no room for it.
    bucket = build_public_page_aggregate_bucket(
        _FakeRequest("/", query={"yclid": "9876543210abcdef"}),
        now=NOW,
    )
    assert bucket is not None
    assert set(bucket.as_dict()) == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS)
    assert "9876543210abcdef" not in json.dumps(bucket.as_dict())


def test_fresh_campaign_replaces_stale_cookie_instead_of_becoming_invalid() -> None:
    stale_payload = {
        "v": PUBLIC_VISIT_ATTRIBUTION_VERSION,
        "utm_source": "old-source",
        "utm_campaign": "old-campaign",
        "landing_path": "/download",
        "first_seen_at": (NOW - timedelta(days=91)).isoformat(),
        "attribution_ref": "graf_visit_0123456789abcdef",
    }

    attribution = read_public_visit_attribution(
        _FakeRequest(
            "/",
            query={"utm_source": "yandex_direct", "utm_campaign": "fresh-campaign"},
            cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: json.dumps(stale_payload)},
        ),
        now=NOW,
    )

    assert attribution["attribution_status"] == "current"
    assert attribution["utm_source"] == "yandex_direct"
    assert attribution["utm_campaign"] == "fresh-campaign"
    assert attribution["attribution_ref"] != stale_payload["attribution_ref"]


def test_a_future_or_expired_visit_cookie_grants_no_campaign() -> None:
    for first_seen_at in (
        NOW + timedelta(minutes=1),
        NOW - timedelta(days=90),
        NOW - timedelta(days=91),
    ):
        payload = {
            "v": PUBLIC_VISIT_ATTRIBUTION_VERSION,
            "utm_source": "yandex_direct",
            "utm_campaign": "forged_or_expired",
            "landing_path": "/download",
            "first_seen_at": first_seen_at.isoformat(),
            "attribution_ref": "graf_visit_0123456789abcdef",
        }
        attribution = read_public_visit_attribution(
            _FakeRequest(
                "/download",
                cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: json.dumps(payload)},
            ),
            now=NOW,
        )
        assert attribution["attribution_status"] == "invalid"
        assert _labels(attribution) == dict.fromkeys(PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS)
        assert attribution["first_seen_at"] is None


def test_a_damaged_visit_record_grants_nothing_and_is_never_trusted() -> None:
    for damaged in (
        "not-json",
        json.dumps({"v": 99, "utm_source": "yandex_direct"}),
        json.dumps({"v": PUBLIC_VISIT_ATTRIBUTION_VERSION, "utm_source": "user@example.com"}),
        json.dumps({"v": PUBLIC_VISIT_ATTRIBUTION_VERSION, "visit_id": "abc"}),
        json.dumps({"v": PUBLIC_VISIT_ATTRIBUTION_VERSION, "landing_path": "/cabinet"}),
        "x" * (PUBLIC_VISIT_ATTRIBUTION_MAX_BYTES + 1),
    ):
        request = _FakeRequest(
            "/download",
            cookies={PUBLIC_VISIT_ATTRIBUTION_COOKIE: damaged},
        )

        attribution = read_public_visit_attribution(request, now=NOW)

        assert attribution["attribution_status"] == "invalid", damaged
        assert _labels(attribution) == dict.fromkeys(PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS), damaged
        assert attribution[PUBLIC_VISIT_ATTRIBUTION_YCLID_FIELD] is None, damaged
        assert attribution["first_seen_at"] is None, damaged
        # Nothing from the damaged record survives. The landing page still comes
        # from the live request, which is the only trustworthy source left.
        assert attribution["landing_path"] == "/download", damaged


def test_public_page_aggregate_bucket_uses_configured_internal_network() -> None:
    request = _FakeRequest("/", client_host="10.20.4.8")
    request.app.state.settings = Settings(product_analytics_internal_hosts=("10.20.0.0/16",))

    bucket = build_public_page_aggregate_bucket(request, now=NOW)

    assert bucket is not None
    assert bucket.traffic_class == "internal"


def test_public_page_aggregate_bucket_defaults_to_external_without_internal_network() -> None:
    request = _FakeRequest("/", client_host="10.20.4.8")

    bucket = build_public_page_aggregate_bucket(request, now=NOW)

    assert bucket is not None
    assert bucket.traffic_class == "external"


def test_public_page_aggregate_bucket_carries_the_visit_campaign_only() -> None:
    _, cookie = _visit(
        "/",
        query={"utm_source": "yandex_direct", "utm_medium": "cpc"},
    )
    assert cookie is not None
    request = _FakeRequest(
        "/download",
        cookies={cookie[0]: cookie[1]},
        headers={"user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"},
    )

    bucket = build_public_page_aggregate_bucket(request, now=NOW)
    assert bucket is not None
    assert set(bucket.as_dict()) == set(ANONYMOUS_AGGREGATE_ALLOWED_FIELDS)
    assert bucket.surface == "public_download"
    assert bucket.landing_path == "/"
    assert bucket.source == "yandex_direct"
    assert bucket.medium == "cpc"
    assert bucket.device_class == "mobile"
    assert bucket.traffic_class == "external"
    serialized = json.dumps(bucket.as_dict())
    assert cookie[1] not in serialized
    assert "iPhone" not in serialized
    assert "203.0.113.10" not in serialized


def test_consent_share_is_published_only_when_it_cannot_point_at_one_person() -> None:
    report = build_public_consent_share_report(aggregate_visits=100, consent_visits=41)

    assert report["published"] is True
    assert report["consent_share"] == 0.41
    assert report["consent_share_percent"] == 41
    assert report["consent_share_label"] == "41 %"
    assert report["blocked_reason"] is None
    assert "обезличенным счётом" in report["caveat"]

    too_small = build_public_consent_share_report(aggregate_visits=2, consent_visits=1)
    assert too_small["published"] is False
    assert too_small["consent_share"] is None
    assert too_small["consent_share_label"] is None
    assert too_small["blocked_reason"] == "below_minimum_bucket_size"

    inconsistent = build_public_consent_share_report(aggregate_visits=10, consent_visits=11)
    assert inconsistent["published"] is False
    assert inconsistent["blocked_reason"] == "counts_inconsistent"

    invalid = build_public_consent_share_report(aggregate_visits=-1, consent_visits=0)
    assert invalid["published"] is False
    assert invalid["blocked_reason"] == "invalid_counts"

    zero_consent = build_public_consent_share_report(aggregate_visits=9, consent_visits=0)
    assert zero_consent["published"] is True
    assert zero_consent["consent_share_label"] == "0 %"
