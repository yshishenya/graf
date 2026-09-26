"""The consent boundary of the public pages (T032, T035, T037, T038).

Two halves are checked together, because the rule is only real when both hold:
the browser controller must not send an optional event without consent (proven by
running the real ``analytics.js`` in a synthetic page), and the first-party relay
must refuse the same request even if a client sends it anyway.

The visitor's decision surface is a third half: FR-004 and FR-006 are about what
the visitor gets and what the counter is configured with, so the real consent
library is rendered in a real browser for those checks.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_CAPTURE_ENDPOINT,
    PUBLIC_ANALYTICS_CONSENT_CATEGORIES,
    PUBLIC_ANALYTICS_CONSENT_VERSION,
    build_public_analytics_context,
    normalize_public_analytics_consent,
)

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tests" / "browser" / "public-analytics-consent.test.cjs"
MODAL_HARNESS = ROOT / "tests" / "browser" / "public-analytics-consent-modal.test.cjs"
NODE = shutil.which("node")
# Rendering the real modal needs an installed Playwright. The browser lane
# installs it into the test directory, and GRAF_NODE_MODULES points at an
# existing installation elsewhere; without either the check is skipped rather
# than reported as a pass.
INSTALLED_NODE_MODULES = ROOT / "tests" / "browser" / "node_modules"
NODE_MODULES = os.environ.get("GRAF_NODE_MODULES") or (
    str(INSTALLED_NODE_MODULES) if (INSTALLED_NODE_MODULES / "playwright").is_dir() else None
)
AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"
# The catalog states which surface an event belongs to; this is the download page
# event, and the page under test is the download page.
EVENT_NAME = "public_download_viewed"
VIEW_ID = "graf_public_view_0123456789abcdef"


def _analytics_settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_replay_enabled=True,
    )


def _event_payload(**overrides: object) -> dict:
    payload = {
        "event_name": EVENT_NAME,
        "page_path": "/download",
        "surface": "public_download",
        "view_id": VIEW_ID,
        "consent_state": "accepted_all",
        "consent_categories": list(PUBLIC_ANALYTICS_CONSENT_CATEGORIES),
    }
    payload.update(overrides)
    return payload


def _stored_download_visits(database_url: str) -> int:
    async def _read() -> int:
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    sa.text(
                        f'select coalesce(sum(visits), 0) from "{AGGREGATE_TABLE}" '
                        "where surface = :surface"
                    ),
                    {"surface": "public_download"},
                )
                return int(result.scalar_one())
        finally:
            await engine.dispose()

    return asyncio.run(_read())


@pytest.mark.skipif(NODE is None, reason="node is required to run the browser controller")
def test_browser_controller_never_sends_an_optional_event_without_consent(tmp_path: Path) -> None:
    """SC-004, FR-059: run the real controller, not a description of it."""
    context = build_public_analytics_context(
        _analytics_settings("postgresql+asyncpg://localhost/analytics_contract"),
        "/download",
    )
    assert context["enabled"] is True
    config_path = tmp_path / "public-analytics-config.json"
    config_path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [NODE, str(HARNESS), str(config_path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "public_analytics_consent_harness=pass" in completed.stdout
    for scenario in (
        "no_decision_sends_nothing",
        "refusal_is_kept_on_a_repeat_visit",
        "damaged_decision_is_a_refusal",
        "consented_event_uses_the_first_party_relay",
        "revocation_stops_optional_sends",
        "provider_failure_does_not_break_the_page",
        "analytics_consent_alone_keeps_behaviour_recording_off",
        "signup_page_view_is_measured_without_form_values",
        "refusal_is_the_same_action_as_consent",
    ):
        assert f"ok {scenario}" in completed.stdout, scenario


@pytest.mark.skipif(NODE is None, reason="node is required to render the consent modal")
@pytest.mark.skipif(
    NODE_MODULES is None,
    reason="Playwright must be installed to render the modal",
)
def test_the_rendered_consent_modal_offers_refusal_as_the_same_single_action() -> None:
    """FR-004: the visitor's real decision surface, not a description of it."""
    completed = subprocess.run(
        [NODE, str(MODAL_HARNESS)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
        env={**os.environ, "GRAF_NODE_MODULES": NODE_MODULES},
        timeout=180,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "public_analytics_consent_modal_harness=pass" in completed.stdout
    for scenario in (
        "refusal_needs_one_keyboard_activation",
        "consent_and_refusal_use_the_same_single_step_path",
        "refusal_is_the_same_action_on_the_signup_page",
    ):
        assert f"ok {scenario}" in completed.stdout, scenario


def test_relay_refuses_an_event_without_a_valid_consent_decision(
    postgres_seeded_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-059: a missing, refused or damaged decision means "do not send"."""
    app = create_app(_analytics_settings(postgres_seeded_database_url))
    delivered: list[dict] = []

    import twobrain_rec_server.public.web as public_web

    def _record(settings: Settings, event: dict) -> dict:
        delivered.append(event)
        return {
            "provider": "posthog",
            "status": "live_safe_sent",
            "delivered": True,
            "retryable": False,
        }

    monkeypatch.setattr(public_web, "deliver_public_analytics_event", _record)

    refused_payloads = {
        "necessary_only": _event_payload(
            consent_state="necessary_only", consent_categories=["necessary"]
        ),
        "revoked": _event_payload(consent_state="revoked", consent_categories=["necessary"]),
        "unknown_state": _event_payload(consent_state="maybe"),
        "no_state": {key: value for key, value in _event_payload().items() if key != "consent_state"},
        "no_categories": {
            key: value for key, value in _event_payload().items() if key != "consent_categories"
        },
        "categories_not_a_list": _event_payload(consent_categories="necessary,analytics"),
        "analytics_category_absent": _event_payload(
            consent_state="customized",
            consent_categories=["necessary", "behavior_replay"],
        ),
    }

    with TestClient(app) as client:
        for label, payload in refused_payloads.items():
            for attempt in (1, 2):  # a repeat visit is refused exactly the same way
                response = client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=payload)
                assert response.status_code == 403, (label, attempt, response.text)
                assert response.json()["reason"] == "optional_consent_not_granted", label
        assert delivered == []

        granted = client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=_event_payload())
        after_grant = [
            client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=payload)
            for payload in refused_payloads.values()
        ]

    assert granted.status_code == 202, granted.text
    assert granted.json()["accepted"] is True
    assert len(delivered) == 1
    assert delivered[0]["event_name"] == EVENT_NAME
    assert delivered[0]["consent_state"] == "accepted_all"
    assert [response.status_code for response in after_grant] == [403] * len(refused_payloads)


def test_relay_refuses_forbidden_material_even_with_consent(
    postgres_seeded_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A granted consent never widens the closed field list of the relay."""
    app = create_app(_analytics_settings(postgres_seeded_database_url))
    delivered: list[dict] = []

    import twobrain_rec_server.public.web as public_web

    monkeypatch.setattr(
        public_web,
        "deliver_public_analytics_event",
        lambda settings, event: delivered.append(event) or {"delivered": True},
    )

    rejected_payloads = {
        "unknown_field": _event_payload(email="visitor@example.com"),
        "unknown_event": _event_payload(event_name="meeting_transcript_viewed"),
        "event_of_another_surface": _event_payload(event_name="public_landing_viewed"),
        "wrong_surface": _event_payload(surface="public_landing"),
        "unknown_category": _event_payload(
            consent_categories=["necessary", "analytics", "telepathy"]
        ),
        "bad_view_id": _event_payload(view_id="short"),
        "unknown_label": _event_payload(section_id="not_a_section"),
        "contact_in_label": _event_payload(cta_location="visitor@example.com"),
    }

    with TestClient(app) as client:
        responses = {
            label: client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=payload)
            for label, payload in rejected_payloads.items()
        }

    assert {label: response.status_code for label, response in responses.items()} == dict.fromkeys(
        rejected_payloads, 400
    )
    assert delivered == []


def test_signup_and_login_page_views_cannot_carry_a_typed_value(
    postgres_seeded_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-027: the credential pages are measured, and never with what was typed.

    Measurement covers sign-up and login, so their page views must be accepted.
    The same acceptance must not become a channel for a form value, so a payload
    that carries one is refused even though its consent decision is valid.
    """
    app = create_app(_analytics_settings(postgres_seeded_database_url))
    delivered: list[dict] = []

    import twobrain_rec_server.public.web as public_web

    monkeypatch.setattr(
        public_web,
        "deliver_public_analytics_event",
        lambda settings, event: delivered.append(event) or {"delivered": True},
    )

    typed_email = "visitor-273@example.test"
    accepted_payloads = {
        "signup": _event_payload(
            event_name="public_signup_viewed", page_path="/sign-up", surface="public_signup"
        ),
        "login": _event_payload(
            event_name="public_login_viewed", page_path="/login", surface="public_login"
        ),
    }
    refused_payloads = {
        "typed_email_field": _event_payload(
            event_name="public_signup_viewed",
            page_path="/sign-up",
            surface="public_signup",
            email=typed_email,
        ),
        "typed_value_in_label": _event_payload(
            event_name="public_signup_viewed",
            page_path="/sign-up",
            surface="public_signup",
            cta_location=typed_email,
        ),
        "typed_value_in_path": _event_payload(
            event_name="public_signup_viewed",
            page_path=f"/sign-up?email={typed_email}",
            surface="public_signup",
        ),
        "login_event_on_signup_page": _event_payload(
            event_name="public_login_viewed", page_path="/sign-up", surface="public_signup"
        ),
    }

    with TestClient(app) as client:
        accepted = {
            label: client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=payload)
            for label, payload in accepted_payloads.items()
        }
        refused = {
            label: client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=payload)
            for label, payload in refused_payloads.items()
        }

    assert {label: response.status_code for label, response in accepted.items()} == dict.fromkeys(
        accepted_payloads, 202
    )
    assert [event["surface"] for event in delivered] == ["public_signup", "public_login"]
    assert all(typed_email not in json.dumps(event) for event in delivered)
    assert {label: response.status_code for label, response in refused.items()} == dict.fromkeys(
        refused_payloads, 400
    )


def test_refusal_does_not_stop_the_anonymous_count(
    postgres_seeded_database_url: str,
) -> None:
    """FR-001, SC-004: the anonymous measurement keeps working after a refusal."""
    app = create_app(_analytics_settings(postgres_seeded_database_url))

    with TestClient(app) as client:
        refused = client.post(
            PUBLIC_ANALYTICS_CAPTURE_ENDPOINT,
            json=_event_payload(consent_state="necessary_only", consent_categories=["necessary"]),
        )
        page = client.get("/download")

    assert refused.status_code == 403
    assert page.status_code == 200
    assert _stored_download_visits(postgres_seeded_database_url) == 1


def test_relay_is_closed_while_public_measurement_is_disabled(client) -> None:
    response = client.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, json=_event_payload())

    assert response.status_code == 403
    assert response.json()["reason"] == "public_measurement_disabled"


def test_relay_is_closed_for_a_cross_origin_post(postgres_seeded_database_url: str) -> None:
    app = create_app(_analytics_settings(postgres_seeded_database_url))

    with TestClient(app) as client:
        response = client.post(
            PUBLIC_ANALYTICS_CAPTURE_ENDPOINT,
            json=_event_payload(),
            headers={"origin": "https://attacker.example.test"},
        )

    assert response.status_code == 403
    assert response.json()["reason"] == "cross_origin"


def test_a_damaged_consent_record_is_read_as_a_denial() -> None:
    """FR-059: an unreadable or inconsistent record grants nothing at all."""
    denied_inputs = (
        None,
        "accepted_all",
        {},
        {"state": "accepted_all"},
        {"state": "accepted_all", "categories": [], "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION},
        {
            "state": "accepted_all",
            "categories": ["telepathy"],
            "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        },
        {
            "state": "accepted_all",
            "categories": "analytics",
            "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        },
        {
            "state": "necessary_only",
            "categories": ["necessary"],
            "copy_version": "2020-01-01.1",
        },
        {
            "state": "accepted_all",
            "categories": ["analytics"],
            "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        },
        {
            "state": "customized",
            "categories": ["necessary", "telepathy"],
            "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        },
    )

    for consent in denied_inputs:
        normalized = normalize_public_analytics_consent(consent)
        assert normalized["state"] == "unknown", consent
        assert normalized["analytics_allowed"] is False, consent
        assert normalized["advertising_attribution_allowed"] is False, consent
        assert normalized["behavior_replay_allowed"] is False, consent

    granted = normalize_public_analytics_consent(
        {
            "state": "accepted_all",
            "categories": list(PUBLIC_ANALYTICS_CONSENT_CATEGORIES),
            "copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
        }
    )
    assert granted["state"] == "accepted_all"
    assert granted["analytics_allowed"] is True
