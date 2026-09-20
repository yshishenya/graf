"""The campaign of a visit becomes the attribute of the client record (T042, T078).

FR-015 is the point of the whole feature: the labels saved on the public page
must survive the registration and end up on the customer record. The rules that
must hold there are proven here without a database, because they are pure:

* the campaign that brought the client is copied, and the confidence says how it
  was obtained (``linked`` — automatically, at registration);
* a registration that has no usable campaign record is written as ``unknown``
  with empty labels, and never as a direct entry (FR-018, FR-024);
* a record outside the 90-day window is not reused (FR-017);
* the steps of the web registration are counted on their own surfaces, each with
  the campaign of the visit (FR-020), and one step can never be read as a page
  view.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    DEFAULT_PUBLIC_LANDING_PATH,
    build_client_acquisition_attribute_from_visit_attribution,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    ANONYMOUS_AGGREGATE_SURFACES,
    INSTALLER_DELIVERY_SURFACE,
    WEB_REGISTRATION_STEP_COMPLETED,
    WEB_REGISTRATION_STEP_FAILED,
    WEB_REGISTRATION_STEP_STARTED,
    WEB_REGISTRATION_STEP_SURFACES,
    registration_step_surface,
)
from twobrain_rec_server.public.analytics import (
    PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS,
    build_public_installer_delivery_bucket,
    build_public_registration_step_bucket,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
CAMPAIGN = {
    "utm_source": "yandex_direct",
    "utm_medium": "cpc",
    "utm_campaign": "2026q3_b2c_launch_ru",
    "utm_id": "987654",
    "utm_content": "creative_a",
    "utm_term": "meeting_notes",
}
YCLID = "1234567890123456789"


class _Request:
    """The smallest request a counted action needs, without a web server."""

    def __init__(
        self,
        *,
        path: str = "/download",
        query: str = "",
        cookie: str | None = None,
        user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        referer: str | None = None,
    ) -> None:
        self.url_path = path
        self.query = query
        self.user_agent = user_agent
        self.referer = referer
        self.cookies = {} if cookie is None else {"graf_visit_attribution": cookie}
        self.client = type("_Client", (), {"host": "203.0.113.10"})()
        self.headers = {"user-agent": user_agent}
        if referer is not None:
            self.headers["referer"] = referer


def _visit_record(
    *,
    status: str = "saved",
    first_seen_at: datetime | None = None,
    landing_path: str | None = "/download",
    labels: dict[str, str | None] | None = None,
    yclid: str | None = YCLID,
    referrer_category: str | None = "paid",
) -> dict[str, str | None]:
    """One record as ``read_public_visit_attribution`` returns it."""
    chosen = CAMPAIGN if labels is None else labels
    return {
        "utm_source": chosen.get("utm_source"),
        "utm_medium": chosen.get("utm_medium"),
        "utm_campaign": chosen.get("utm_campaign"),
        "utm_id": chosen.get("utm_id"),
        "utm_content": chosen.get("utm_content"),
        "utm_term": chosen.get("utm_term"),
        "yclid": yclid,
        "referrer_category": referrer_category,
        "landing_path": landing_path,
        "first_seen_at": (first_seen_at or NOW).isoformat(),
        "attribution_status": status,
    }


def test_a_known_campaign_is_copied_onto_the_client_record() -> None:
    """FR-015: the labels of the visit become the attribute of the record."""
    account_id = uuid4()
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=account_id,
        attribution=_visit_record(),
        captured_at=NOW,
    )

    assert attribute.account_id == account_id
    assert attribute.source == "yandex_direct"
    assert attribute.medium == "cpc"
    assert attribute.campaign == "2026q3_b2c_launch_ru"
    assert attribute.content == "creative_a"
    assert attribute.term == "meeting_notes"
    assert attribute.yclid == YCLID
    assert attribute.landing_path == "/download"
    assert attribute.attribution_rule == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    # Transferred automatically at registration, without the visitor doing
    # anything: that is exactly the ``linked`` level.
    assert attribute.attribution_confidence == "linked"
    assert attribute.captured_at == NOW
    # The stored attribute never carries the raw account identifier as a payload.
    assert attribute.as_analytics_dict()["account_pseudonym"] != str(account_id)
    assert str(account_id) not in str(attribute.as_analytics_dict())


@pytest.mark.parametrize("status", ["missing", "invalid"])
def test_an_unknown_campaign_is_recorded_as_unknown_and_never_as_direct(status: str) -> None:
    """FR-018, FR-024: no cookie and a damaged cookie both mean "unknown"."""
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(status=status, labels=dict.fromkeys(
            PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS
        ), yclid=None),
        captured_at=NOW,
    )

    assert attribute.attribution_confidence == "unknown"
    assert attribute.attribution_confidence != "direct"
    for name in ("source", "medium", "campaign", "content", "term", "yclid"):
        assert getattr(attribute, name) is None
    # The column cannot be empty, so the documented public default is used — not
    # an invented path, and not the private page the visitor was on.
    assert attribute.landing_path == DEFAULT_PUBLIC_LANDING_PATH


def test_a_missing_record_grants_nothing() -> None:
    """A registration with no record at all is still recorded as unknown."""
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=None,
        captured_at=NOW,
    )

    assert attribute.attribution_confidence == "unknown"
    assert attribute.campaign is None
    assert attribute.landing_path == DEFAULT_PUBLIC_LANDING_PATH


def test_a_future_record_is_not_reused() -> None:
    future = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(first_seen_at=NOW + timedelta(minutes=1)),
        captured_at=NOW,
    )

    assert future.attribution_confidence == "unknown"
    assert future.campaign is None


def test_a_record_outside_the_window_is_not_reused() -> None:
    """FR-017: the campaign of a visit older than 90 days is not copied."""
    expired = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(first_seen_at=NOW - timedelta(days=91)),
        captured_at=NOW,
    )
    inside = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(first_seen_at=NOW - timedelta(days=89)),
        captured_at=NOW,
    )

    assert expired.attribution_confidence == "unknown"
    assert expired.campaign is None
    assert inside.attribution_confidence == "linked"
    assert inside.campaign == CAMPAIGN["utm_campaign"]


def test_a_click_identifier_without_labels_is_still_a_known_source() -> None:
    """FR-016: a Yandex click is a known paid source even without labels."""
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(
            status="current",
            labels=dict.fromkeys(PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS),
        ),
        captured_at=NOW,
    )

    assert attribute.yclid == YCLID
    assert attribute.campaign is None
    assert attribute.attribution_confidence == "linked"


def test_a_private_landing_page_is_never_stored() -> None:
    """Only published public pages may be stored as the landing page."""
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(landing_path="/cabinet/meetings"),
        captured_at=NOW,
    )

    assert attribute.landing_path == DEFAULT_PUBLIC_LANDING_PATH


def test_a_label_that_looks_like_contact_data_is_dropped() -> None:
    """The attribute passes the same sanitizer as the aggregate (FR-010)."""
    attribute = build_client_acquisition_attribute_from_visit_attribution(
        account_id=uuid4(),
        attribution=_visit_record(
            labels={**CAMPAIGN, "utm_campaign": "call +7 916 123-45-67 now"}
        ),
        captured_at=NOW,
    )

    assert attribute.campaign is None
    assert attribute.source == "yandex_direct"
    # Some labels survived, so the attribute is still a known campaign.
    assert attribute.attribution_confidence == "linked"


def test_the_step_catalog_is_closed_and_separate_from_the_pages() -> None:
    """FR-020: three known steps, each on its own surface, none of them a page."""
    assert tuple(WEB_REGISTRATION_STEP_SURFACES) == (
        WEB_REGISTRATION_STEP_STARTED,
        WEB_REGISTRATION_STEP_COMPLETED,
        WEB_REGISTRATION_STEP_FAILED,
    )
    assert not set(WEB_REGISTRATION_STEP_SURFACES.values()) & set(ANONYMOUS_AGGREGATE_SURFACES)
    assert INSTALLER_DELIVERY_SURFACE not in ANONYMOUS_AGGREGATE_SURFACES
    with pytest.raises(ValueError, match="unknown web registration step"):
        registration_step_surface("signup_almost_done")


@pytest.mark.parametrize(
    ("step", "surface"),
    [
        (WEB_REGISTRATION_STEP_STARTED, "public_signup_step_viewed"),
        (WEB_REGISTRATION_STEP_COMPLETED, "public_signup_completed"),
        (WEB_REGISTRATION_STEP_FAILED, "public_signup_failed"),
    ],
)
def test_every_registration_step_keeps_the_campaign_of_the_visit(
    step: str, surface: str
) -> None:
    """FR-020: начало, успех и отказ — each with the campaign of the visit."""
    request = _Request()
    bucket = build_public_registration_step_bucket(
        request, step, attribution=_visit_record(), now=NOW
    )

    assert bucket.surface == surface
    assert bucket.landing_path == "/download"
    assert bucket.source == "yandex_direct"
    assert bucket.medium == "cpc"
    assert bucket.campaign == CAMPAIGN["utm_campaign"]
    assert bucket.content == "creative_a"
    assert bucket.term == "meeting_notes"
    assert bucket.referrer_category == "paid"
    assert bucket.visits == 1
    # A step is not a page, and its counter holds no identifier at all.
    assert bucket.surface not in ANONYMOUS_AGGREGATE_SURFACES
    stored = {key: str(value) for key, value in bucket.as_dict().items()}
    assert "203.0.113.10" not in str(stored)
    assert request.user_agent not in str(stored)


def test_a_step_without_a_campaign_stays_unknown() -> None:
    """FR-024: a counted step never reports a direct entry it did not see."""
    bucket = build_public_registration_step_bucket(
        _Request(),
        WEB_REGISTRATION_STEP_COMPLETED,
        attribution=_visit_record(
            status="invalid",
            labels=dict.fromkeys(PUBLIC_VISIT_ATTRIBUTION_LABEL_FIELDS),
            yclid=None,
            landing_path=None,
            referrer_category=None,
        ),
        now=NOW,
    )

    assert bucket.surface == "public_signup_completed"
    assert bucket.source is None
    assert bucket.campaign is None
    assert bucket.referrer_category == "unknown"
    assert bucket.landing_path == DEFAULT_PUBLIC_LANDING_PATH


def test_the_installer_delivery_keeps_the_campaign_of_the_visit() -> None:
    """FR-019: the delivered file is counted with the campaign it came from."""
    bucket = build_public_installer_delivery_bucket(
        _Request(path="/static/public/downloads/graf.pkg", query="v=abc123"),
        attribution=_visit_record(),
        now=NOW,
    )

    assert bucket.surface == INSTALLER_DELIVERY_SURFACE
    assert bucket.landing_path == "/download"
    assert bucket.campaign == CAMPAIGN["utm_campaign"]
    assert bucket.visits == 1
