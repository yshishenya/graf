from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID
from tests.unit.test_explicit_product_funnel import Provider, settings
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper


def setup(client, monkeypatch):
    cfg = settings()
    monkeypatch.setattr(client.app.state, "settings", cfg)
    provider = Provider()
    monkeypatch.setattr(PostHogClientWrapper, "from_settings", lambda _: provider)
    return cfg, provider


def test_current_consent_identity_durable_receipt_and_withdrawal(client, monkeypatch):
    cfg, provider = setup(client, monkeypatch)
    headers = auth_headers()
    url = "/api/v1/product-analytics/"
    assert (
        client.get(url + "explicit-context", headers=headers).json()["telemetry_gate_state"]
        == "not_seen"
    )
    event = {"event_name": "desktop_first_opened", "properties": {}}
    assert client.post(url + "explicit-events", headers=headers, json=event).status_code == 403
    assert provider.calls == []
    accepted = client.put(
        url + "explicit-consent",
        headers=headers,
        json={"accepted": True, "copy_version": cfg.product_analytics_consent_copy_version},
    )
    assert accepted.status_code == 200
    expected = build_safe_identity(user_source_id=str(USER_ID)).posthog_distinct_id
    assert accepted.json()["stable_pseudonymous_user_id"] == expected
    assert (
        client.get(url + "explicit-context", headers=headers).json()["telemetry_gate_state"]
        == "accepted"
    )
    first = client.post(url + "explicit-events", headers=headers, json=event)
    assert first.status_code == 200
    assert first.json()["provider_accepted"] is True
    assert first.json()["ingestion_verified"] is False
    assert len(provider.calls) == 2  # server-owned account connection and first observed launch
    assert {x["distinct_id"] for x in provider.calls} == {expected}
    assert (
        client.post(url + "explicit-events", headers=headers, json=event).json()["status"]
        == "duplicate"
    )
    assert len(provider.calls) == 2
    assert (
        client.put(
            url + "explicit-consent",
            headers=headers,
            json={"accepted": False, "copy_version": cfg.product_analytics_consent_copy_version},
        ).status_code
        == 200
    )
    assert client.post(url + "explicit-events", headers=headers, json=event).status_code == 403
    assert len(provider.calls) == 2


def test_forged_identity_failure_retry_and_anonymous_access(client, monkeypatch):
    cfg, provider = setup(client, monkeypatch)
    headers = auth_headers()
    url = "/api/v1/product-analytics/"
    assert (
        client.put(
            url + "explicit-consent",
            headers=headers,
            json={"accepted": True, "copy_version": cfg.product_analytics_consent_copy_version},
        ).status_code
        == 200
    )
    forged = {
        "event_name": "first_recording_completed",
        "properties": {},
        "stable_pseudonymous_user_id": "graf_pseudo_user_" + "b" * 32,
    }
    assert client.post(url + "explicit-events", headers=headers, json=forged).status_code == 403
    assert provider.calls == []
    assert client.get(url + "explicit-context").status_code in (400, 401, 403)
    provider.status = "network_error"
    event = {"event_name": "first_recording_completed", "properties": {}}
    assert client.post(url + "explicit-events", headers=headers, json=event).status_code == 503
    first_uuid = provider.calls[0]["explicit_event_id"]
    provider.status = "live_safe_sent"
    assert client.post(url + "explicit-events", headers=headers, json=event).status_code == 200
    assert provider.calls[1]["explicit_event_id"] == first_uuid
    assert (
        client.post(url + "explicit-events", headers=headers, json=event).json()["status"]
        == "duplicate"
    )
    assert len(provider.calls) == 3


def test_withdrawal_persists_while_configuration_disabled(client, monkeypatch):
    cfg, provider = setup(client, monkeypatch)
    headers = auth_headers()
    url = "/api/v1/product-analytics/"
    assert (
        client.put(
            url + "explicit-consent",
            headers=headers,
            json={"accepted": True, "copy_version": cfg.product_analytics_consent_copy_version},
        ).status_code
        == 200
    )
    monkeypatch.setattr(
        client.app.state,
        "settings",
        cfg.model_copy(update={"product_analytics_explicit_funnel_enabled": False}),
    )
    assert (
        client.put(
            url + "explicit-consent",
            headers=headers,
            json={"accepted": False, "copy_version": "old-version"},
        ).status_code
        == 200
    )
    monkeypatch.setattr(client.app.state, "settings", cfg)
    assert (
        client.get(url + "explicit-context", headers=headers).json()["telemetry_gate_state"]
        == "withdrawn"
    )
    assert (
        client.post(
            url + "explicit-events",
            headers=headers,
            json={"event_name": "desktop_first_opened", "properties": {}},
        ).status_code
        == 403
    )
    assert provider.calls == []
