from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.explicit_funnel import (
    change_consent,
    context_for,
    deliver_milestone,
)
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService


def settings():
    return Settings(
        env="development",
        product_analytics_explicit_funnel_enabled=True,
        product_analytics_legal_approved=True,
        product_analytics_privacy_approved=True,
        product_analytics_consent_copy_version="synthetic-existing-notice-v1",
        product_analytics_posthog_autocapture_enabled=False,
        product_analytics_posthog_web_direct_enabled=False,
    )


class Provider:
    def __init__(self, status="live_safe_sent"):
        self.calls = []
        self.status = status

    def capture_event(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(status=self.status)


def payload(user="synthetic-user-A", name="desktop_first_opened"):
    return {
        "event_name": name,
        "stable_pseudonymous_user_id": build_safe_identity(user_source_id=user).posthog_distinct_id,
        "occurred_at": datetime.now(UTC),
        "properties": {},
    }


def accepted(cfg):
    return change_consent(
        cfg, None, accepted=True, copy_version=cfg.product_analytics_consent_copy_version
    )


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"consent": {"state": "withdrawn"}},
        {"consent": {"state": "accepted", "copy_version": "old"}},
    ],
)
def test_missing_withdrawn_stale_consent_never_delivers(state):
    provider = Provider()
    with pytest.raises(ValueError):
        deliver_milestone(
            settings(),
            user_id="synthetic-user-A",
            state=state,
            payload=payload(),
            provider=provider,
        )
    assert provider.calls == []


def test_operator_configuration_never_implies_personal_acceptance():
    assert (
        context_for(settings(), user_id="synthetic-user-A", state=None)["telemetry_gate_state"]
        == "not_seen"
    )
    with pytest.raises(ValueError):
        change_consent(settings(), None, accepted=True, copy_version="old")
    assert (
        context_for(Settings(), user_id="synthetic-user-A", state=accepted(settings()))["enabled"]
        is False
    )


def test_forged_and_workspace_identity_rejected():
    cfg = settings()
    for identity in (
        build_safe_identity(user_source_id="synthetic-user-B").posthog_distinct_id,
        "graf_pseudo_workspace_" + "a" * 32,
    ):
        event = payload()
        event["stable_pseudonymous_user_id"] = identity
        provider = Provider()
        with pytest.raises(ValueError):
            deliver_milestone(
                cfg,
                user_id="synthetic-user-A",
                state=accepted(cfg),
                payload=event,
                provider=provider,
            )
        assert provider.calls == []


def test_failure_retries_same_uuid_then_durable_receipt_deduplicates():
    cfg = settings()
    state = accepted(cfg)
    provider = Provider("network_error")
    state, receipt = deliver_milestone(
        cfg, user_id="synthetic-user-A", state=state, payload=payload(), provider=provider
    )
    assert receipt["accepted"] is False
    assert "milestones" not in state
    first_uuid = provider.calls[0]["explicit_event_id"]
    provider.status = "live_safe_sent"
    state, receipt = deliver_milestone(
        cfg, user_id="synthetic-user-A", state=state, payload=payload(), provider=provider
    )
    assert receipt["provider_accepted"] is True
    assert receipt["ingestion_verified"] is False
    assert provider.calls[1]["explicit_event_id"] == first_uuid
    _, duplicate = deliver_milestone(
        cfg, user_id="synthetic-user-A", state=state, payload=payload(), provider=provider
    )
    assert duplicate["status"] == "duplicate"
    assert len(provider.calls) == 2


def test_same_user_pseudonym_for_all_explicit_milestones_and_no_history():
    cfg = settings()
    state = accepted(cfg)
    provider = Provider()
    for name in (
        "desktop_first_opened",
        "desktop_account_connected",
        "first_recording_completed",
        "first_result_viewed",
        "first_value_session_completed",
    ):
        state, receipt = deliver_milestone(
            cfg,
            user_id="synthetic-user-A",
            state=state,
            payload=payload(name=name),
            provider=provider,
        )
        assert receipt["accepted"]
    assert len({x["distinct_id"] for x in provider.calls}) == 1
    assert len({x["explicit_event_id"] for x in provider.calls}) == 5
    with pytest.raises(ValueError):
        deliver_milestone(
            cfg,
            user_id="synthetic-user-A",
            state=state,
            payload=payload(name="payment_succeeded"),
            provider=provider,
        )
    state = change_consent(
        cfg, state, accepted=False, copy_version=cfg.product_analytics_consent_copy_version
    )
    with pytest.raises(ValueError):
        deliver_milestone(
            cfg, user_id="synthetic-user-A", state=state, payload=payload(), provider=provider
        )


def test_legacy_claim_based_ingest_blocked_in_minimal_mode():
    cfg = settings().model_copy(update={"product_analytics_enabled": True})
    receipt = ProductAnalyticsIngestService(cfg).ingest(payload(), telemetry_gate_state="accepted")
    assert receipt.accepted is False
    assert receipt.status == "explicit_context_required"


@pytest.mark.parametrize(
    "body,expected",
    [
        ("{}", "provider_receipt_invalid"),
        ('{"status":0}', "provider_receipt_invalid"),
        ("not-json", "provider_receipt_invalid"),
        ('{"status":1}', "live_safe_sent"),
    ],
)
def test_http_200_receipt_and_no_ip_boundary(tmp_path, monkeypatch, body, expected):
    import json

    from twobrain_rec_server.product_analytics import posthog_client

    key_file = tmp_path / "synthetic-capture-key"
    key_file.write_text("synthetic-only-not-a-real-provider-key")
    cfg = settings().model_copy(
        update={
            "product_analytics_posthog_enabled": True,
            "product_analytics_posthog_host": "https://provider.example.test",
            "product_analytics_posthog_project_key_file": key_file,
            "product_analytics_validation_mode": "live_safe",
        }
    )
    calls = []
    client = posthog_client.PostHogClientWrapper(
        enabled=True,
        host="https://provider.example.test",
        project_key_file=key_file,
        project_key_present=True,
        validation_mode="live_safe",
        live_delivery_allowed=True,
        settings=cfg,
        transport=lambda url, headers, data, timeout: (
            calls.append(json.loads(data))
            or posthog_client.ProviderTransportResponse(status_code=200, body=body)
        ),
    )
    # Synthetic isolated proof only: production readiness is never changed.
    monkeypatch.setattr(
        posthog_client,
        "resolve_provider_delivery_gate",
        lambda *a, **k: SimpleNamespace(allowed=True),
    )
    result = client.capture_event(
        event_name="desktop_first_opened",
        distinct_id=build_safe_identity(user_source_id="synthetic-user-A").posthog_distinct_id,
        properties={},
        explicit_event_id="00000000-0000-5000-8000-000000000001",
    )
    assert result.status == expected
    assert calls[0]["properties"]["$geoip_disable"] is True
    assert calls[0]["properties"]["$ip"] is None
    assert calls[0]["uuid"] == "00000000-0000-5000-8000-000000000001"
    assert "synthetic-only" not in str(result.as_dict())


@pytest.mark.parametrize(
    "properties",
    [
        {"useful_result_type": "Synthetic private conversation about an unreleased project"},
        {"stable_pseudonymous_user_id": "raw_account_12345"},
        {"useful_result_type": {"account": "synthetic-raw-id"}},
        {"utm_campaign": "private_internal_launch"},
        {"utm_source": "private_internal_launch"},
    ],
)
def test_closed_categories_reject_content_and_nested_identity_before_provider(properties):
    cfg = settings()
    event = payload(name="first_value_session_completed")
    event["properties"] = properties
    provider = Provider()
    with pytest.raises(ValueError):
        deliver_milestone(
            cfg, user_id="synthetic-user-A", state=accepted(cfg), payload=event, provider=provider
        )
    assert provider.calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"product_analytics_explicit_funnel_enabled": False},
        {"product_analytics_legal_approved": False},
        {"product_analytics_consent_copy_version": "new-version"},
    ],
)
def test_withdrawal_remains_durable_when_mode_readiness_or_version_changes(changes):
    cfg = settings()
    state = accepted(cfg)
    blocked = cfg.model_copy(update=changes)
    withdrawn = change_consent(blocked, state, accepted=False, copy_version="old-version")
    assert withdrawn["consent"]["state"] == "withdrawn"
    assert (
        context_for(cfg, user_id="synthetic-user-A", state=withdrawn)["telemetry_gate_state"]
        == "withdrawn"
    )
