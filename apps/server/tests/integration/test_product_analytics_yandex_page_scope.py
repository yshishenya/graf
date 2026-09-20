import time
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_readiness import (
    BACKUP_STATE_FILE_ENV,
    RESTORE_STATE_FILE_ENV,
    RETENTION_STATE_FILE_ENV,
)
from twobrain_rec_server.public.analytics import (
    build_product_yandex_provider_context,
    build_public_analytics_context,
)


def test_093_public_yandex_scope_is_preserved_for_landing_and_download() -> None:
    settings = Settings(
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
    )

    assert build_public_analytics_context(settings, "/")["enabled"] is True
    assert build_public_analytics_context(settings, "/download")["enabled"] is True
    assert build_public_analytics_context(settings, "/")["external_counter_allowed"] is True
    assert build_public_analytics_context(settings, "/download")["external_counter_allowed"] is True

    # FR-027: the login page is a public page and is measured by consent, but the
    # external counter keeps its published two-page scope, so the credential page
    # is measured through the first-party relay only.
    login = build_public_analytics_context(settings, "/login")
    assert login["enabled"] is True
    assert login["surface"] == "public_login"
    assert login["external_counter_allowed"] is False
    assert login["replay_allowed"] is False
    assert login["webvisor_allowed"] is False
    assert login["click_map_allowed"] is False
    assert login["form_analytics_allowed"] is False


def _live_gate_environment(tmp_path: Path) -> dict[str, str]:
    now = int(time.time())
    backup = tmp_path / "backup"
    backup.write_text(
        "backup_state_version=1\nlast_attempt_result=pass\n"
        f"last_success_epoch={now - 3600}\ncopies_local=2\ncopies_offsite=1\n",
        encoding="utf-8",
    )
    restore = tmp_path / "restore"
    restore.write_text(
        "restore_state_version=1\nlast_verify_result=pass\n"
        f"last_verify_epoch={now - 3600}\n",
        encoding="utf-8",
    )
    retention = tmp_path / "retention"
    retention.write_text(
        "retention_state_version=1\nresult=pass\n"
        "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl enforcement_verified=true\n"
        "category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true\n"
        "category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task enforcement_verified=true\n"
        "category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true\n",
        encoding="utf-8",
    )
    approvals = tmp_path / "approvals"
    approvals.write_text(
        "approval_state_version=1\n"
        + "\n".join(
            f"approval kind={kind} state=recorded approved_by=release_owner approved_at=2026-09-18 scope=measurement_scope evidence_ref=ref-{kind}"
            for kind in ("legal", "privacy", "security", "qa", "rollback", "delivery", "check")
        )
        + "\n",
        encoding="utf-8",
    )
    access = tmp_path / "access"
    digest = "sha256:" + "a" * 64
    access.write_text(
        "access_governance_state_version=1\nreviewed_at=0\nexpires_at=4102444800\n"
        "accepted_operator_count=2\nmfa_operator_count=2\n"
        f"repository_digest={digest}\nconfig_digest={digest}\ninstalled_guard_digest={digest}\n"
        "revocation_review=complete\ncredential_rotation_review=complete\naudit_review=complete\n",
        encoding="utf-8",
    )
    basis = tmp_path / "basis"
    basis.write_text("legal_basis_state_version=1\n", encoding="utf-8")
    return {
        "GRAF_POSTHOG_BACKUP_STATE_FILE": str(backup),
        "GRAF_POSTHOG_RESTORE_STATE_FILE": str(restore),
        RETENTION_STATE_FILE_ENV: str(retention),
        "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE": str(approvals),
        "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": str(access),
        "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE": str(basis),
    }


def test_096_yandex_product_page_context_is_inventory_gated(tmp_path: Path) -> None:
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="live_safe",
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_legal_approved=True,
        product_analytics_privacy_approved=True,
        product_analytics_security_approved=True,
        product_analytics_qa_approved=True,
        product_analytics_disclosure_approved=True,
        product_analytics_dashboard_ready=True,
        product_analytics_provider_smoke_approved=True,
        product_analytics_rollback_approved=True,
        product_analytics_live_provider_delivery_approved=True,
    )

    environment = _live_gate_environment(tmp_path)
    public_context = build_product_yandex_provider_context(
        settings, "public_landing", environ=environment
    )
    admin_context = build_product_yandex_provider_context(settings, "admin", environ=environment)
    future_context = build_product_yandex_provider_context(
        settings, "future_browser_page", environ=environment
    )
    meeting_context = build_product_yandex_provider_context(
        settings, "meeting_result_detail", environ=environment
    )

    assert public_context["enabled"] is True
    assert public_context["counter_id"] == "12345678"
    assert admin_context["enabled"] is False
    assert admin_context["blocked_reason"] == "inventory_blocked"
    assert future_context["enabled"] is False
    assert future_context["blocked_reason"] == "inventory_blocked"
    assert meeting_context["enabled"] is False
    assert meeting_context["blocked_reason"] == "replay_unavailable"


def test_browser_controller_has_inventory_aware_yandex_gate() -> None:
    from pathlib import Path

    repo_root = Path(__file__).parents[4]
    analytics_js = (
        repo_root / "apps/server/src/twobrain_rec_server/public/static/public/analytics.js"
    ).read_text(encoding="utf-8")

    assert "isYandexPageAllowed" in analytics_js
    assert "pageConfig.yandex_state === \"approved_page_view_event\"" in analytics_js
    assert "api.providerBlocked = true" in analytics_js
    assert "initializeProductYandexProvider(productConfig)" in analytics_js
    assert "bindProductYandexUserID" in analytics_js
    assert "\"setUserID\"" in analytics_js
    assert "\"userParams\"" in analytics_js
    assert 'window.ym(counterId, "hit", "/__graf/" + pageClass' in analytics_js
    assert "params: { page_class: pageClass }" in analytics_js
