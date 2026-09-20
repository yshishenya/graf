import time
from datetime import UTC, datetime
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.advertising_transfer import (
    ADVERTISING_TRANSFER_STATE_FILE_ENV,
    OptionalMeasurementConsent,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse
from twobrain_rec_server.product_analytics.provider_readiness import (
    BACKUP_STATE_FILE_ENV,
    RESTORE_STATE_FILE_ENV,
    RETENTION_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.yandex_offline import (
    YandexOfflineConversionExporter,
    build_yandex_offline_conversion,
    is_yandex_offline_event_allowed,
)

CONSENT_REVISION = "2026-09-15.1"

# The visitor-facing copy read while a transfer is under test: it names the
# advertising platform, the category and the offline-conversion transfer.
DISCLOSED_PAGES = {
    "analytics_consent": (
        f"Редакция {CONSENT_REVISION} от 15 сентября 2026 года. "
        "Категория «Рекламная атрибуция» отдельно разрешает передачу данных "
        "в рекламную платформу Яндекс Метрика для офлайн-конверсий."
    ),
    "cookies": "Cookie «Рекламная атрибуция» хранит только решение посетителя.",
}
# The same page names the platform but says nothing about offline conversions.
UNDISCLOSED_PAGES = {
    "analytics_consent": (
        f"Редакция {CONSENT_REVISION}. Категория «Рекламная атрибуция» разрешает "
        "измерение на сайте и передачу данных в рекламную платформу Яндекс Метрика."
    ),
}

BASIS_LINE = (
    "basis recipient=yandex_metrica purpose=yandex_offline_conversions "
    "state=confirmed basis=consent confirmed_by=privacy_reviewer "
    "confirmed_at=2026-09-18 scope=offline_conversion_transfer_basis "
    "evidence_ref=ev-273-transfer-basis"
)
REVOCATION_LINE = (
    "revocation recipient=yandex_metrica purposes=yandex_offline_conversions "
    "revoked_at=2026-09-18 delivery_state=confirmed method=provider_support_request "
    "delivered_at=2026-09-19 evidence_ref=ev-273-revocation"
)


def _approved_event(name: str = "desktop_account_connected", *, properties: dict | None = None):
    event_properties = {
        "auth_method_category": "oauth_provider",
        "account_connection_state": "connected",
        "bridge_present": True,
        "yandex_client_id_present": True,
        "yandex_user_id_present": True,
        "yclid_present": False,
        "attribution_reliability": "campaign_linked_reliable",
    }
    if properties is not None:
        event_properties.update(properties)
    return build_activation_event(
        name,
        stable_pseudonymous_user_id="graf_pseudo_user_7a0de00000000000",
        occurred_at=datetime(2026, 7, 9, 10, 0, tzinfo=UTC),
        properties=event_properties,
    )


def _granted_consent() -> OptionalMeasurementConsent:
    """The visitor decision, which the delivery caller hands over explicitly."""

    return OptionalMeasurementConsent(state="granted")


def _live_settings(oauth_file: Path, **overrides) -> Settings:
    arguments = {
        "product_analytics_enabled": True,
        "product_analytics_validation_mode": "live_safe",
        "product_analytics_provider_mode": "parallel_measurement",
        "product_analytics_yandex_offline_enabled": True,
        "product_analytics_yandex_counter_id": "12345678",
        "product_analytics_yandex_oauth_token_file": oauth_file,
        "product_analytics_legal_approved": True,
        "product_analytics_privacy_approved": True,
        "product_analytics_security_approved": True,
        "product_analytics_qa_approved": True,
        "product_analytics_disclosure_approved": True,
        "product_analytics_dashboard_ready": True,
        "product_analytics_provider_smoke_approved": True,
        "product_analytics_rollback_approved": True,
        "product_analytics_live_provider_delivery_approved": True,
    }
    arguments.update(overrides)
    return Settings(**arguments)


def _register_environ(tmp_path: Path, *lines: str) -> dict[str, str]:
    path = tmp_path / "advertising-transfers"
    path.write_text(
        "\n".join(("advertising_transfer_state_version=1", *lines)) + "\n", encoding="utf-8"
    )
    return {ADVERTISING_TRANSFER_STATE_FILE_ENV: str(path)}


def _write_live_gate_evidence(tmp_path: Path) -> dict[str, str]:
    now = int(time.time())
    backup = tmp_path / "backup-state"
    backup.write_text(
        "\n".join(
            (
                "backup_state_version=1",
                "last_attempt_result=pass",
                f"last_success_epoch={now - 3600}",
                "copies_local=2",
                "copies_offsite=1",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    restore = tmp_path / "restore-state"
    restore.write_text(
        "\n".join(
            (
                "restore_state_version=1",
                "last_verify_result=pass",
                f"last_verify_epoch={now - 2 * 86400}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    retention = tmp_path / "retention-state"
    retention.write_text(
        "\n".join(
            (
                "retention_state_version=1",
                "result=pass",
                "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl enforcement_verified=true",
                "category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true",
                "category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task enforcement_verified=true",
                "category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    approvals = tmp_path / "launch-approvals"
    approvals.write_text(
        "\n".join(
            (
                "approval_state_version=1",
                *(
                    f"approval kind={kind} state=recorded approved_by=release_owner approved_at=2026-09-18 scope=measurement_scope evidence_ref=ref-{kind}"
                    for kind in ("legal", "privacy", "security", "qa", "rollback", "delivery", "check")
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    access = tmp_path / "access-governance-state"
    digest = "sha256:" + "a" * 64
    access.write_text(
        "\n".join(
            (
                "access_governance_state_version=1",
                f"reviewed_at={now - 60}",
                f"expires_at={now + 86400}",
                "accepted_operator_count=2",
                "mfa_operator_count=2",
                f"repository_digest={digest}",
                f"config_digest={digest}",
                f"installed_guard_digest={digest}",
                "revocation_review=complete",
                "credential_rotation_review=complete",
                "audit_review=complete",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        BACKUP_STATE_FILE_ENV: str(backup),
        RESTORE_STATE_FILE_ENV: str(restore),
        RETENTION_STATE_FILE_ENV: str(retention),
        "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE": str(approvals),
        "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": str(access),
        "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE": str(tmp_path / "missing-withdrawals"),
    }


def _live_exporter(
    tmp_path: Path,
    *,
    lines: tuple[str, ...] = (BASIS_LINE,),
    environ: dict[str, str] | None = None,
    pages: dict[str, str] | None = None,
    **settings_overrides,
) -> tuple[YandexOfflineConversionExporter, list[tuple[str, dict, bytes]]]:
    oauth_file = tmp_path / "yandex_oauth_token"
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")
    calls: list[tuple[str, dict, bytes]] = []

    def fake_transport(
        url: str, headers: dict, body: bytes, timeout: float
    ) -> ProviderTransportResponse:
        calls.append((url, dict(headers), body))
        return ProviderTransportResponse(status_code=200, body='{"uploading":{"id":1}}')

    exporter = YandexOfflineConversionExporter.from_settings(
        _live_settings(oauth_file, **settings_overrides),
        environ=(
            environ
            if environ is not None
            else {
                **_register_environ(tmp_path, *lines),
                **_write_live_gate_evidence(tmp_path),
            }
        ),
        site_pages=DISCLOSED_PAGES if pages is None else pages,
    )
    exporter.transport = fake_transport
    return exporter, calls


def test_yandex_offline_subset_rejects_unapproved_product_events() -> None:
    assert is_yandex_offline_event_allowed("desktop_account_connected") is True
    assert is_yandex_offline_event_allowed("first_value_session_completed") is True
    assert is_yandex_offline_event_allowed("desktop_first_opened") is False


def test_yandex_offline_row_uses_redacted_identity_source_and_dedupe_key() -> None:
    row = build_yandex_offline_conversion(_approved_event())
    payload = row.as_dict()

    assert payload["event_name"] == "desktop_account_connected"
    assert payload["identity_kind"] == "UserId"
    assert payload["identity_value_source"] == "graf_pseudonymous_user_redacted"
    assert payload["conversion_unix_time"] == "1783591200"
    assert payload["upload_state"] == "queued"
    assert payload["dedupe_key"].startswith("graf_yandex_dedupe_")
    assert payload["upload_batch_id"].startswith("graf_yandex_batch_")
    assert "graf_pseudo_user_7a0de00000000000" not in str(payload)


def test_yandex_offline_exporter_returns_redacted_dry_run_status(tmp_path: Path) -> None:
    oauth_file = tmp_path / "yandex_oauth_token"
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")
    exporter = YandexOfflineConversionExporter.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="parallel_measurement",
            product_analytics_yandex_offline_enabled=True,
            product_analytics_yandex_counter_id="12345678",
            product_analytics_yandex_oauth_token_file=oauth_file,
        )
    )

    result = exporter.export(_approved_event())

    assert result.status == "dry_run"
    assert result.provider == "yandex_offline"
    assert result.retryable is False
    assert "synthetic-yandex-token" not in str(result.as_dict())
    assert "12345678" not in str(result.as_dict())


def test_yandex_offline_duplicate_key_is_stable_for_same_event() -> None:
    first = build_yandex_offline_conversion(_approved_event())
    second = build_yandex_offline_conversion(_approved_event())

    assert first.dedupe_key == second.dedupe_key


def test_yandex_offline_does_not_treat_stable_user_id_as_yandex_userid_without_page_binding() -> None:
    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id="graf_pseudo_user_7a0de00000000000",
        occurred_at=datetime(2026, 7, 9, 10, 0, tzinfo=UTC),
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
            "yandex_client_id_present": True,
            "yclid_present": False,
            "attribution_reliability": "needs_runtime_client_id_resolver",
        },
    )

    row = build_yandex_offline_conversion(event)

    assert row.identity_kind == "ClientId"
    assert row.identity_value_source == "runtime_yandex_client_id_redacted"


def test_yandex_live_safe_upload_uses_multipart_without_result_value_leak(tmp_path: Path) -> None:
    exporter, calls = _live_exporter(tmp_path)

    result = exporter.export(_approved_event(), visitor_consent=_granted_consent())

    assert result.status == "live_safe_uploaded"
    assert "/management/v1/counter/12345678/offline_conversions/upload" in calls[0][0]
    assert "type=BASIC" in calls[0][0]
    assert calls[0][1]["Authorization"] == "OAuth synthetic-yandex-token"
    assert calls[0][1]["Content-Type"].startswith("multipart/form-data")
    assert b"Target,DateTime,UserId,PurchaseId" in calls[0][2]
    assert b"desktop_account_connected" in calls[0][2]
    assert b"graf_pseudo_user_7a0de00000000000" in calls[0][2]
    result_body = result.as_dict()
    assert "synthetic-yandex-token" not in str(result_body)
    assert "12345678" not in str(result_body)
    assert "graf_pseudo_user_7a0de00000000000" not in str(result_body)


def test_yandex_live_upload_is_refused_without_a_recorded_transfer_basis(
    tmp_path: Path,
) -> None:
    exporter, calls = _live_exporter(tmp_path, environ={})

    result = exporter.export(_approved_event(), visitor_consent=_granted_consent())

    assert calls == [], "a transfer without a basis must not reach the provider"
    assert result.status == "transfer_not_authorised"
    assert result.retryable is False
    assert result.metadata["blockers"] == ["advertising_legal_basis_missing"]
    assert result.metadata["transfer_facts"]["basis_state"] is None
    assert result.metadata["recipient"] == "yandex_metrica"
    assert result.metadata["transfer_ref"].startswith("graf_yandex_dedupe_")
    assert "graf_pseudo_user_7a0de00000000000" not in str(result.as_dict())


def test_yandex_live_upload_is_refused_when_the_visitor_was_not_told(
    tmp_path: Path,
) -> None:
    exporter, calls = _live_exporter(tmp_path, pages=UNDISCLOSED_PAGES)

    result = exporter.export(_approved_event(), visitor_consent=_granted_consent())

    assert calls == []
    assert result.status == "transfer_not_authorised"
    assert result.metadata["blockers"] == ["visitor_disclosure_incomplete"]
    assert result.metadata["transfer_facts"]["disclosure_missing_statements"] == [
        "offline_conversions_named"
    ]


def test_yandex_live_upload_is_refused_without_the_visitor_decision(tmp_path: Path) -> None:
    exporter, calls = _live_exporter(tmp_path)

    without_decision = exporter.export(_approved_event())
    denied = exporter.export(
        _approved_event(), visitor_consent=OptionalMeasurementConsent(state="denied")
    )

    assert calls == []
    for result in (without_decision, denied):
        assert result.status == "transfer_not_authorised"
    assert without_decision.metadata["blockers"] == ["advertising_attribution_consent_missing"]
    assert denied.metadata["blockers"] == ["advertising_attribution_consent_denied"]


def test_yandex_live_upload_does_not_read_the_secret_before_the_basis_is_settled(
    tmp_path: Path,
) -> None:
    exporter, calls = _live_exporter(tmp_path, environ={})
    # The secret file still exists, so the exporter is configured; only the
    # legal basis is missing. The refusal must come before any secret is read.
    exporter.oauth_token_file.unlink()

    result = exporter.export(_approved_event(), visitor_consent=_granted_consent())

    assert calls == []
    assert result.status == "transfer_not_authorised"


def test_yandex_provider_smoke_never_transfers_even_without_a_basis(tmp_path: Path) -> None:
    exporter, calls = _live_exporter(
        tmp_path,
        environ={},
        pages={},
        product_analytics_validation_mode="provider_smoke",
    )

    result = exporter.export(_approved_event())

    assert calls == []
    assert result.status == "dry_run", "smoke mode performs no transfer, so it needs no basis"


def test_yandex_revoked_recipient_stops_the_transfer_and_leaves_a_trace(
    tmp_path: Path,
) -> None:
    exporter, calls = _live_exporter(tmp_path, lines=(BASIS_LINE, REVOCATION_LINE))

    first = exporter.export(_approved_event(), visitor_consent=_granted_consent())
    second = exporter.export(_approved_event(), visitor_consent=_granted_consent())

    assert calls == [], "a withdrawn consent must stop every further transfer"
    for result in (first, second):
        assert result.status == "recipient_revoked"
        assert result.retryable is False
        assert "recipient_revocation_recorded" in result.metadata["blockers"]
        trace = result.metadata["revocation_trace"]
        assert trace["recipient"] == "yandex_metrica"
        assert trace["delivery_state"] == "confirmed"
        assert trace["delivered_at"] == "2026-09-19"
        lines = result.metadata["revocation_state_lines"]
        assert any("revocation recipient=yandex_metrica" in line for line in lines)
        assert "graf_pseudo_user_7a0de00000000000" not in str(result.as_dict())


def test_yandex_retransfer_of_already_refused_data_is_refused_again(tmp_path: Path) -> None:
    event = _approved_event()
    # The reference of a transfer is the identifier the provider would receive,
    # so refusing it by this value refuses exactly this piece of data.
    reference = build_yandex_offline_conversion(event).dedupe_key

    refusal_line = (
        "revocation_refusal recipient=yandex_metrica purpose=yandex_offline_conversions "
        f"transfer_ref={reference} refused_at=2026-09-20 reason=recipient_revocation_recorded"
    )
    exporter, calls = _live_exporter(
        tmp_path, lines=(BASIS_LINE, REVOCATION_LINE, refusal_line)
    )

    result = exporter.export(event, visitor_consent=_granted_consent())

    assert calls == []
    assert result.status == "recipient_revoked"
    assert result.metadata["blockers"] == [
        "recipient_revocation_recorded",
        "retransfer_of_revoked_data_refused",
    ]
    assert reference in result.metadata["revocation_trace"]["refused_transfer_refs"]
    assert result.metadata["transfer_ref"] == reference
