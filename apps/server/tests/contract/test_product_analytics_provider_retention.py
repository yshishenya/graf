from twobrain_rec_server.product_analytics.retention import (
    provider_lifecycle_records,
    retention_rules,
)


def test_provider_lifecycle_records_cover_posthog_yandex_and_evidence_boundaries() -> None:
    records = provider_lifecycle_records()
    keys = {(record.provider, record.data_class) for record in records}

    assert ("posthog", "activation_event") in keys
    assert ("posthog", "autocapture_event") in keys
    assert ("posthog", "replay_recording") in keys
    assert ("posthog", "backup") in keys
    assert ("yandex_metrica", "offline_conversion") in keys
    assert ("yandex_metrica", "provider_aggregate") in keys
    assert ("graf_metadata", "delivery_gap_record") in keys
    assert all(record.evidence_state in {"documented", "verified"} for record in records)
    assert all(record.dashboard_caveat for record in records)
    assert all(record.export_policy != "content_bearing_committed" for record in records)


def test_provider_retention_keeps_minimum_ninety_days_and_truthful_deletion_scope() -> None:
    assert all(rule.minimum_retention_days >= 90 for rule in retention_rules())

    records = provider_lifecycle_records()
    posthog_autocapture = next(
        record for record in records if record.provider == "posthog" and record.data_class == "autocapture_event"
    )
    yandex_offline = next(
        record for record in records if record.provider == "yandex_metrica" and record.data_class == "offline_conversion"
    )
    replay = next(record for record in records if record.provider == "posthog" and record.data_class == "replay_recording")

    assert posthog_autocapture.retention_days >= 90
    assert posthog_autocapture.deletion_scope == "provider_operator_action"
    assert yandex_offline.deletion_scope == "not_promised"
    assert "already uploaded" in yandex_offline.dashboard_caveat
    assert replay.storage_location == "not_collected_by_default"
