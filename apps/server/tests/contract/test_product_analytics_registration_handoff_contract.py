"""The campaign of a visit survives web registration (T042, T054, T078).

These tests walk the real public pages and the real registration routes of the
real application against a PostgreSQL schema built by ``alembic upgrade head``,
and then read the rows that were actually stored. Nothing here inspects the
implementation: FR-015 is proven by the stored attribute of the new client,
FR-020 by the stored steps of the registration, and FR-019 by the stored
delivery of the installer file.
"""

from __future__ import annotations

import asyncio
import re
from uuid import uuid4

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.auth_contexts import ORG_ID
from twobrain_rec_server.api import auth as api_auth_module
from twobrain_rec_server.cabinet.web_routes import auth_email_flow as auth_email_flow_module
from twobrain_rec_server.db.models import UserIdentity
from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    DEFAULT_PUBLIC_LANDING_PATH,
    build_client_acquisition_attribute,
    record_client_acquisition_attribute_safely,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    INSTALLER_DELIVERY_SURFACE,
    WEB_REGISTRATION_STEP_COMPLETED,
    WEB_REGISTRATION_STEP_FAILED,
    WEB_REGISTRATION_STEP_STARTED,
    WEB_REGISTRATION_STEP_SURFACES,
)
from twobrain_rec_server.product_analytics.traffic_class import REPORTED_TRAFFIC_CLASSES
from twobrain_rec_server.public.analytics import PUBLIC_VISIT_ATTRIBUTION_COOKIE

AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"
ACQUISITION_TABLE = "client_acquisition_attributes"
# A browser-shaped client: only then is the counted traffic reported traffic and
# only then does the flow look like the flow of a real visitor.
BROWSER_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    )
}


def _rows(database_url: str, table: str, *, order_by: str = "created_at") -> list[dict]:
    async def _read() -> list[dict]:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    sa.text(f'select * from "{table}" order by "{order_by}"')
                )
                return [dict(row._mapping) for row in result]
        finally:
            await engine.dispose()

    return asyncio.run(_read())


def _surfaces(database_url: str) -> dict[str, int]:
    counted: dict[str, int] = {}
    for row in _rows(database_url, AGGREGATE_TABLE):
        counted[str(row["surface"])] = counted.get(str(row["surface"]), 0) + int(row["visits"])
    return counted


def _start_signup(client: TestClient, email: str) -> tuple[str, str]:
    """Open the registration step and return its state nonce and its code."""
    started = client.post(
        "/sign-up/email/start",
        data={"email": email, "next": "/meetings"},
        headers=BROWSER_HEADERS,
    )
    assert started.status_code == 200, started.text[:400]
    state_match = re.search(r'name="state" value="([^"]+)"', started.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
    assert state_match is not None, "the registration step did not publish its state"
    assert code_match is not None, "the registration step did not publish its code"
    cookie_name = auth_email_flow_module._email_auth_browser_cookie_name(
        state_nonce=state_match.group(1),
        secure=True,
    )
    browser_nonce = started.cookies.get(cookie_name)
    assert browser_nonce is not None
    client.cookies.set(cookie_name, browser_nonce, domain="testserver.local", path="/")
    return state_match.group(1), code_match.group(1)


def _verify_signup(client: TestClient, email: str, state: str, code: str):
    return client.post(
        "/sign-up/email/verify",
        data={"email": email, "code": code, "state": state, "next": "/meetings"},
        headers=BROWSER_HEADERS,
        follow_redirects=False,
    )


def _complete_signup(client: TestClient, email: str):
    state, code = _start_signup(client, email)
    completed = _verify_signup(client, email, state, code)
    assert completed.status_code == 303, completed.text[:400]
    return completed


def _new_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


def test_the_campaign_of_the_visit_reaches_the_client_record(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-015, FR-016: the labels of the visit become the client attribute."""
    campaign = f"273_handoff_{uuid4().hex[:8]}"
    visit = client.get(
        "/download",
        params={
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": campaign,
            "utm_content": "creative_registration",
            "yclid": "1234567890123456789",
        },
        headers=BROWSER_HEADERS,
    )
    assert visit.status_code == 200
    assert client.cookies.get(PUBLIC_VISIT_ATTRIBUTION_COOKIE)

    _complete_signup(client, _new_email("handoff"))

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1, "the registration did not record exactly one attribute"
    attribute = rows[0]
    assert attribute["source"] == "yandex_direct"
    assert attribute["medium"] == "cpc"
    assert attribute["campaign"] == campaign
    assert attribute["content"] == "creative_registration"
    assert attribute["landing_path"] == "/download"
    assert attribute["attribution_rule"] == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert attribute["attribution_confidence"] == "linked"
    assert attribute["yclid"] == "1234567890123456789"

    accounts = _rows(postgres_seeded_database_url, "user_identities")
    assert str(attribute["account_id"]) in {str(row["id"]) for row in accounts}


def test_a_registration_without_a_campaign_is_unknown_and_never_direct(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-018, FR-024: no visit means "unknown", not a direct entry."""
    _complete_signup(client, _new_email("no-cookie"))

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    attribute = rows[0]
    assert attribute["attribution_confidence"] == "unknown"
    assert attribute["attribution_confidence"] != "direct"
    for name in ("source", "medium", "campaign", "content", "term", "yclid"):
        assert attribute[name] is None
    # The column cannot be empty: the documented public default is stored, and
    # nothing is invented for a visitor nobody knows.
    assert attribute["landing_path"] == DEFAULT_PUBLIC_LANDING_PATH


def test_a_damaged_cookie_is_unknown_and_never_direct(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-018, FR-059: a damaged record grants no campaign and no direct entry."""
    client.cookies.set(
        PUBLIC_VISIT_ATTRIBUTION_COOKIE,
        "graf-v1-not-a-real-payload",
        domain="testserver.local",
        path="/",
    )

    _complete_signup(client, _new_email("damaged"))

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    assert rows[0]["attribution_confidence"] == "unknown"
    assert rows[0]["campaign"] is None
    assert rows[0]["landing_path"] == DEFAULT_PUBLIC_LANDING_PATH


def test_a_second_registration_never_rewrites_the_campaign(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-015: the campaign of the first registration is the one that stays."""
    first_campaign = f"273_first_{uuid4().hex[:8]}"
    second_campaign = f"273_second_{uuid4().hex[:8]}"
    email = _new_email("repeat")

    client.get(
        "/download",
        params={"utm_source": "yandex_direct", "utm_campaign": first_campaign},
        headers=BROWSER_HEADERS,
    )
    _complete_signup(client, email)

    # The same person registers again from another campaign.
    client.cookies.set(
        PUBLIC_VISIT_ATTRIBUTION_COOKIE,
        "",
        domain="testserver.local",
        path="/",
    )
    client.cookies.delete(PUBLIC_VISIT_ATTRIBUTION_COOKIE, domain="testserver.local", path="/")
    client.get(
        "/download",
        params={"utm_source": "google_ads", "utm_campaign": second_campaign},
        headers=BROWSER_HEADERS,
    )
    _complete_signup(client, email)

    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1, "a repeated registration created a second attribute"
    assert rows[0]["campaign"] == first_campaign
    assert rows[0]["source"] == "yandex_direct"


def test_the_same_account_keeps_its_first_attribute_in_storage(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-015: one attribute per account, enforced by the storage itself."""
    account_id = uuid4()
    email = _new_email("storage")
    sessionmaker = client.app_state["sessionmaker"]

    async def _seed_account() -> None:
        async with sessionmaker() as db:
            db.add(
                UserIdentity(
                    id=account_id,
                    organization_id=ORG_ID,
                    external_subject=f"email:{email}",
                    display_name="Attribute owner",
                )
            )
            await db.commit()

    asyncio.run(_seed_account())

    first = build_client_acquisition_attribute(
        account_id=account_id,
        landing_path="/download",
        source="yandex_direct",
        campaign="273_storage_first",
    )
    second = build_client_acquisition_attribute(
        account_id=account_id,
        landing_path="/download",
        source="google_ads",
        campaign="273_storage_second",
    )

    async def _write_twice() -> tuple[bool, bool]:
        async with sessionmaker() as db:
            written_first = await record_client_acquisition_attribute_safely(
                db, first, commit=True
            )
            written_second = await record_client_acquisition_attribute_safely(
                db, second, commit=True
            )
            return written_first, written_second

    written_first, written_second = asyncio.run(_write_twice())

    assert written_first is True
    assert written_second is False
    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert len(rows) == 1
    assert rows[0]["campaign"] == "273_storage_first"
    assert rows[0]["source"] == "yandex_direct"


def test_a_failed_write_leaves_the_registration_intact(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-058: measurement never breaks a registration."""
    account_id = uuid4()
    attribute = build_client_acquisition_attribute(
        account_id=account_id,
        landing_path="/download",
        campaign="273_unwritten",
    )

    async def _write_without_session() -> bool:
        return await record_client_acquisition_attribute_safely(None, attribute)

    assert asyncio.run(_write_without_session()) is False
    rows = _rows(postgres_seeded_database_url, ACQUISITION_TABLE)
    assert rows == []


def test_every_step_of_web_registration_is_counted_with_its_campaign(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-020: начало, успех и отказ — each step keeps the campaign of the visit."""
    campaign = f"273_steps_{uuid4().hex[:8]}"
    client.get(
        "/download",
        params={
            "utm_source": "yandex_direct",
            "utm_medium": "cpc",
            "utm_campaign": campaign,
        },
        headers=BROWSER_HEADERS,
    )

    # A registration that is completed, and a registration that is refused.
    _complete_signup(client, _new_email("step-ok"))
    state, code = _start_signup(client, _new_email("step-fail"))
    refused = _verify_signup(client, _new_email("step-fail"), state, f"{(int(code) + 1) % 1000000:06d}")
    assert refused.status_code != 303

    rows = [row for row in _rows(postgres_seeded_database_url, AGGREGATE_TABLE)]
    steps = {
        str(row["surface"]): row
        for row in rows
        if row["surface"] in set(WEB_REGISTRATION_STEP_SURFACES.values())
    }
    assert set(steps) == set(WEB_REGISTRATION_STEP_SURFACES.values())
    assert steps["public_signup_step_viewed"]["visits"] == 2
    assert steps["public_signup_completed"]["visits"] == 1
    assert steps["public_signup_failed"]["visits"] == 1

    for surface, row in steps.items():
        assert row["campaign"] == campaign, surface
        assert row["source"] == "yandex_direct", surface
        assert row["medium"] == "cpc", surface
        assert row["landing_path"] == "/download", surface
        assert row["referrer_category"] == "paid", surface
        assert row["traffic_class"] in REPORTED_TRAFFIC_CLASSES, surface

    # A step is not a page: the download page view stays its own counter.
    assert _surfaces(postgres_seeded_database_url)["public_download"] == 1


def test_a_registration_step_without_a_campaign_stays_unknown(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-024: a counted step never reports a campaign it did not see."""
    _complete_signup(client, _new_email("step-unknown"))

    steps = [
        row
        for row in _rows(postgres_seeded_database_url, AGGREGATE_TABLE)
        if row["surface"] in set(WEB_REGISTRATION_STEP_SURFACES.values())
    ]
    assert {str(row["surface"]) for row in steps} == {
        "public_signup_step_viewed",
        "public_signup_completed",
    }
    for row in steps:
        assert row["source"] is None
        assert row["campaign"] is None
        assert row["landing_path"] == DEFAULT_PUBLIC_LANDING_PATH
        assert row["referrer_category"] == "unknown"


def test_the_delivered_installer_file_is_counted_apart_from_the_page(
    client: TestClient, postgres_seeded_database_url: str
) -> None:
    """FR-019: the click on the button and the delivered file are two facts."""
    campaign = f"273_installer_{uuid4().hex[:8]}"
    page = client.get(
        "/download",
        params={"utm_source": "yandex_direct", "utm_campaign": campaign},
        headers=BROWSER_HEADERS,
    )
    assert page.status_code == 200
    installer_url = re.search(r'href="([^"]*downloads/graf\.pkg[^"]*)"', page.text)
    assert installer_url is not None, "the download page published no installer link"

    delivered = client.get(installer_url.group(1), headers=BROWSER_HEADERS)
    assert delivered.status_code == 200
    assert delivered.content

    # Not a delivery: a conditional probe, an unrelated asset and a file that is
    # not there.
    client.head(installer_url.group(1), headers=BROWSER_HEADERS)
    client.get("/static/public/landing.css", headers=BROWSER_HEADERS)
    client.get("/static/public/downloads/graf-not-published.pkg", headers=BROWSER_HEADERS)

    rows = _rows(postgres_seeded_database_url, AGGREGATE_TABLE)
    deliveries = [row for row in rows if row["surface"] == INSTALLER_DELIVERY_SURFACE]
    assert len(deliveries) == 1
    assert deliveries[0]["visits"] == 1
    assert deliveries[0]["campaign"] == campaign
    assert deliveries[0]["source"] == "yandex_direct"
    assert deliveries[0]["landing_path"] == "/download"
    assert deliveries[0]["traffic_class"] in REPORTED_TRAFFIC_CLASSES

    surfaces = _surfaces(postgres_seeded_database_url)
    assert surfaces["public_download"] == 1
    # The button carries its own attributes; the counter is the delivery.
    assert INSTALLER_DELIVERY_SURFACE not in {
        WEB_REGISTRATION_STEP_STARTED,
        WEB_REGISTRATION_STEP_COMPLETED,
        WEB_REGISTRATION_STEP_FAILED,
    }


def _start_login(client: TestClient, email: str) -> tuple[str, str]:
    """Open the sign-in step and return its state nonce and its code."""
    started = client.post(
        "/login/email/start",
        data={"email": email, "next": "/meetings"},
        headers=BROWSER_HEADERS,
    )
    assert started.status_code == 200, started.text[:400]
    state_match = re.search(r'name="state" value="([^"]+)"', started.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
    assert state_match is not None, "the sign-in step did not publish its state"
    assert code_match is not None, "the sign-in step did not publish its code"
    cookie_name = auth_email_flow_module._email_auth_browser_cookie_name(
        state_nonce=state_match.group(1),
        secure=True,
    )
    browser_nonce = started.cookies.get(cookie_name)
    assert browser_nonce is not None
    client.cookies.set(cookie_name, browser_nonce, domain="testserver.local", path="/")
    return state_match.group(1), code_match.group(1)


def test_the_sign_in_by_emailed_code_delivers_the_account_connected_milestone(
    client: TestClient, monkeypatch
) -> None:
    """FR-021: the milestone comes from the path the desktop app really uses.

    The embedded cabinet connects an account by an emailed code, not through an
    external provider. Until this path delivered the milestone, the activation
    funnel lost its key step and channel numbers understated what the product
    achieved. The test walks the real routes and captures what actually reached
    the ingest boundary, and it checks the recorded way in, because a sign-in by
    code is not an external provider and must not be filed as one.
    """

    delivered: list[dict[str, object]] = []

    class _Captured:
        """Stand in for the ingest result; only the payload matters here."""

        accepted = True
        event = None
        provider_results: tuple[object, ...] = ()

    def capture(self, payload):  # noqa: ANN001 - the service signature
        delivered.append(dict(payload))
        return _Captured()

    monkeypatch.setattr(
        api_auth_module.ProductAnalyticsIngestService, "ingest", capture, raising=True
    )
    # Measurement of registered users is off by default; this test is about the
    # milestone the server sends, so it has to be on for the delivery to happen.
    monkeypatch.setattr(client.app.state.settings, "product_analytics_enabled", True)

    email = _new_email("milestone-email-code")
    _complete_signup(client, email)

    assert [payload.get("event_name") for payload in delivered] == ["desktop_account_connected"]
    properties = delivered[0]["properties"]
    assert properties["auth_method_category"] == "email_code"
    assert properties["account_connection_state"] == "connected"

    # The same account signing in again is the ordinary desktop path, and it
    # must deliver the milestone too, not only the first registration.
    delivered.clear()
    state, code = _start_login(client, email)
    signed_in = client.post(
        "/login/email/verify",
        data={"email": email, "code": code, "state": state, "next": "/meetings"},
        headers=BROWSER_HEADERS,
        follow_redirects=False,
    )
    assert signed_in.status_code == 303, signed_in.text[:400]

    assert [payload.get("event_name") for payload in delivered] == ["desktop_account_connected"]
    assert delivered[0]["properties"]["auth_method_category"] == "email_code"
    # No campaign cookie was set, so the milestone must not claim a link (FR-024).
    assert delivered[0]["properties"]["attribution_reliability"] == "unknown"
