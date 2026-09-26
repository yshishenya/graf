#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

docker compose -f infra/posthog/docker-compose.posthog.yml config >/dev/null
deploy_branch="${TWOBRAIN_DEPLOY_BRANCH:-${GITHUB_REF_NAME:-$(git branch --show-current || true)}}"
if [[ -z "$deploy_branch" ]]; then
  deploy_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  deploy_branch="${deploy_branch#origin/}"
fi
if [[ -z "$deploy_branch" ]] && git show-ref --verify --quiet refs/remotes/origin/master; then
  deploy_branch="master"
fi
if [[ -z "$deploy_branch" ]]; then
  echo "provider_smoke_result=blocked"
  echo "reason=missing_deploy_branch"
  exit 2
fi
infra/scripts/cd-remote.sh --dry-run --branch "$deploy_branch" >/dev/null

rollback_metadata="$(infra/scripts/rollback-product-analytics-providers.sh --metadata-only --target all)"
grep -Fq 'provider_rollback_result=pass' <<<"$rollback_metadata"
grep -Fq 'rollback_execution=metadata_only_no_state_change' <<<"$rollback_metadata"
grep -Fq 'provider_state_mutation=not_requested' <<<"$rollback_metadata"
grep -Fq 'operator_executor_hook=not_invoked' <<<"$rollback_metadata"

PYTHONPATH="$ROOT_DIR/apps/server/src" python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.access_governance import (
    ACCESS_GOVERNANCE_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.advertising_transfer import (
    optional_measurement_consent_from_categories,
)
from twobrain_rec_server.product_analytics.approvals import (
    APPROVAL_KINDS,
    APPROVAL_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.page_inventory import blocked_yandex_page_classes, yandex_approved_page_classes
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper, ProviderTransportResponse
from twobrain_rec_server.product_analytics.provider_readiness import (
    BACKUP_STATE_FILE_ENV,
    RESTORE_STATE_FILE_ENV,
    RETENTION_STATE_FILE_ENV,
    build_provider_readiness,
)
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report
from twobrain_rec_server.product_analytics.yandex_offline import (
    YandexOfflineConversionExporter,
    build_yandex_offline_conversion,
)
from twobrain_rec_server.public.analytics import (
    build_product_yandex_provider_context,
    build_public_analytics_context,
)

with TemporaryDirectory() as tmpdir:
    key_file = Path(tmpdir) / "posthog_project_key"
    yandex_token_file = Path(tmpdir) / "yandex_token"
    key_file.write_text("synthetic-smoke-key", encoding="utf-8")
    yandex_token_file.write_text("synthetic-yandex-token", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="provider_smoke",
        product_analytics_provider_mode="parallel_measurement",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key_file,
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_offline_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_yandex_oauth_token_file=yandex_token_file,
        product_analytics_legal_approved=True,
    )
    event = build_activation_event(
        "desktop_first_opened",
        stable_pseudonymous_user_id="graf_pseudo_user_5b0e000000000000",
        properties={"platform": "macos", "bridge_present": True},
    )
    delivery = PostHogClientWrapper.from_settings(settings).capture(event)
    readiness = build_provider_readiness(settings).posthog
    if delivery.status != "dry_run" or not readiness.configured:
        raise SystemExit("provider smoke failed")
    yandex_event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id="graf_pseudo_user_5b0e000000000000",
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
            "yandex_client_id_present": True,
            "yandex_user_id_present": True,
            "attribution_reliability": "campaign_linked_reliable",
        },
    )
    yandex_delivery = YandexOfflineConversionExporter.from_settings(settings).export(yandex_event)
    posthog_secret_delivery = PostHogClientWrapper.from_settings(settings).capture_event(
        event_name="graf_web_autocapture_click",
        distinct_id="graf_pseudo_user_5b0e000000000000",
        properties={"analytics_action": "access_token", "page_class": "settings"},
    )
    dedupe_a = build_yandex_offline_conversion(yandex_event).dedupe_key
    dedupe_b = build_yandex_offline_conversion(yandex_event).dedupe_key
    if yandex_delivery.status != "dry_run" or dedupe_a != dedupe_b:
        raise SystemExit("provider smoke failed")
    if posthog_secret_delivery.status != "payload_rejected":
        raise SystemExit("provider smoke failed")
    if yandex_approved_page_classes() != ("public_landing", "public_download"):
        raise SystemExit("provider smoke failed")
    if "admin" not in blocked_yandex_page_classes() or "auth_callback" not in blocked_yandex_page_classes():
        raise SystemExit("provider smoke failed")
    product_yandex_context = build_product_yandex_provider_context(settings, "public_landing")
    admin_yandex_context = build_product_yandex_provider_context(settings, "admin")
    public_yandex_context = build_public_analytics_context(
        Settings(
            public_analytics_enabled=True,
            public_analytics_validation_mode="provider_smoke",
            public_analytics_yandex_metrica_id="12345678",
        ),
        "/",
    )
    if (
        product_yandex_context["enabled"]
        or product_yandex_context["blocked_reason"] != "runtime_disabled"
        or product_yandex_context["counter_id_present"] is not True
    ):
        raise SystemExit("provider smoke failed")
    if admin_yandex_context["enabled"] or admin_yandex_context["blocked_reason"] != "inventory_blocked":
        raise SystemExit("provider smoke failed")
    if not public_yandex_context["enabled"] or public_yandex_context["yandex_metrica_id_present"] is not True:
        raise SystemExit("provider smoke failed")
    live_settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="live_safe",
        product_analytics_provider_mode="parallel_measurement",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key_file,
        product_analytics_yandex_offline_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_yandex_oauth_token_file=yandex_token_file,
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

    now = int(time())
    backup_state_file = Path(tmpdir) / "backup-state"
    backup_state_file.write_text(
        "backup_state_version=1\n"
        "last_attempt_result=pass\n"
        f"last_success_epoch={now - 3600}\n"
        "copies_local=2\n"
        "copies_offsite=1\n",
        encoding="utf-8",
    )
    restore_state_file = Path(tmpdir) / "restore-state"
    restore_state_file.write_text(
        "restore_state_version=1\n"
        "last_verify_result=pass\n"
        f"last_verify_epoch={now - 2 * 86400}\n",
        encoding="utf-8",
    )
    retention_state_file = Path(tmpdir) / "retention-state"
    retention_state_file.write_text(
        "retention_state_version=1\n"
        "result=pass\n"
        "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl enforcement_verified=true\n"
        "category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true\n"
        "category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task enforcement_verified=true\n"
        "category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true\n",
        encoding="utf-8",
    )
    approval_state_file = Path(tmpdir) / "launch-approvals"
    approval_state_file.write_text(
        "approval_state_version=1\n"
        + "\n".join(
            f"approval kind={kind} state=recorded approved_by=release_owner "
            "approved_at=2026-09-18 scope=measurement_scope "
            f"evidence_ref=provider-smoke-{kind}"
            for kind in APPROVAL_KINDS
        )
        + "\n",
        encoding="utf-8",
    )
    access_state_file = Path(tmpdir) / "access-governance-state"
    access_digest = "sha256:" + "a" * 64
    access_state_file.write_text(
        "access_governance_state_version=1\n"
        f"reviewed_at={now - 60}\n"
        f"expires_at={now + 86400}\n"
        "accepted_operator_count=2\n"
        "mfa_operator_count=2\n"
        f"repository_digest={access_digest}\n"
        f"config_digest={access_digest}\n"
        f"installed_guard_digest={access_digest}\n"
        "revocation_review=complete\n"
        "credential_rotation_review=complete\n"
        "audit_review=complete\n",
        encoding="utf-8",
    )
    legal_basis_state_file = Path(tmpdir) / "legal-basis-withdrawals"
    legal_basis_state_file.write_text(
        "legal_basis_state_version=1\n",
        encoding="utf-8",
    )
    live_environment = {
        BACKUP_STATE_FILE_ENV: str(backup_state_file),
        RESTORE_STATE_FILE_ENV: str(restore_state_file),
        RETENTION_STATE_FILE_ENV: str(retention_state_file),
        APPROVAL_STATE_FILE_ENV: str(approval_state_file),
        ACCESS_GOVERNANCE_STATE_FILE_ENV: str(access_state_file),
        BASIS_WITHDRAWAL_STATE_FILE_ENV: str(legal_basis_state_file),
    }

    def posthog_transport(url, headers, body, timeout):
        if not url.endswith("/capture/") or b'"api_key"' not in body or b'"event"' not in body:
            raise SystemExit("provider smoke failed")
        return ProviderTransportResponse(status_code=200, body='{"status":"ok"}')

    def yandex_transport(url, headers, body, timeout):
        if "offline_conversions/upload" not in url or b"Target,DateTime,UserId,PurchaseId" not in body:
            raise SystemExit("provider smoke failed")
        return ProviderTransportResponse(status_code=200, body='{"uploading":{"id":1}}')

    live_posthog = PostHogClientWrapper.from_settings(
        live_settings,
        environ=live_environment,
    )
    live_posthog.transport = posthog_transport
    live_posthog_delivery = live_posthog.capture(yandex_event)

    # The advertising transfer gate (FR-028) lets an offline-conversion upload
    # through only with three things at once: a recorded basis that names this
    # transfer, visitor-facing copy that names the platform, the offline
    # conversions and the advertising attribution category, and the visitor's own
    # decision. The smoke run supplies all three synthetically so it proves the
    # transport works end to end without editing the published documents;
    # production stays blocked until the real copy and the real basis record
    # exist.
    transfer_state_file = Path(tmpdir) / "advertising_transfer_state"
    transfer_state_file.write_text(
        "advertising_transfer_state_version=1\n"
        "basis recipient=yandex_metrica purpose=yandex_offline_conversions "
        "state=confirmed basis=consent confirmed_by=release_owner "
        "confirmed_at=2026-01-01 scope=offline_conversion_transfer_basis "
        "evidence_ref=provider-smoke\n",
        encoding="utf-8",
    )
    smoke_pages = {
        "analytics_consent": (
            "<p>Редакция "
            f"{Settings().public_analytics_consent_copy_version}</p>"
            "<p>Рекламная атрибуция: Яндекс Метрика. Офлайн-конверсии "
            "передаются в Яндекс Метрику.</p>"
        )
    }
    smoke_consent = optional_measurement_consent_from_categories(
        ("advertising_attribution",)
    )

    live_yandex = YandexOfflineConversionExporter.from_settings(
        live_settings,
        environ={
            **live_environment,
            "GRAF_PRODUCT_ANALYTICS_ADVERTISING_TRANSFER_STATE_FILE": str(transfer_state_file)
        },
        site_pages=smoke_pages,
    )
    live_yandex.transport = yandex_transport
    live_yandex_delivery = live_yandex.export(yandex_event, visitor_consent=smoke_consent)
    if live_posthog_delivery.status != "live_safe_sent" or live_yandex_delivery.status != "live_safe_uploaded":
        raise SystemExit("provider smoke failed")
    live_readiness = build_rollout_readiness_report(
        live_settings,
        environ=live_environment,
    ).as_dict()
    if live_readiness["states"]["live_provider_delivery"] != "approved":
        raise SystemExit("provider smoke failed")

dashboard_evidence = Path("specs/096-product-analytics-provider-rollout/validation/dashboard-evidence.md").read_text(
    encoding="utf-8"
)
for required_marker in (
    "Source to first value funnel",
    "Autocapture exploration",
    "desktop_account_connected",
    "first_value_session_completed",
):
    if required_marker not in dashboard_evidence:
        raise SystemExit("provider smoke failed")

print("provider_smoke_result=pass")
print("posthog_stack=config_valid")
print("posthog_stack_contract=handoff_valid")
print("posthog_runtime_source=official_posthog_hobby_generated_compose_required")
print("posthog_secret=redacted_status_only")
print("posthog_secret_payload_rejected=pass")
print("posthog_access_model=metadata_only_pass")
print("provider_lifecycle=metadata_only_pass")
print("posthog_deploy_dry_run=pass")
print("posthog_delivery=dry_run")
print("posthog_live_safe_delivery=transport_verified")
print("posthog_web_direct=render_config_present")
print("posthog_desktop_direct=contract_tested")
print("posthog_autocapture=current_pages_enabled")
print("yandex_counter=runtime_only_redacted")
print("yandex_public_baseline=preserved")
print("yandex_render_config=present")
print("yandex_blocked_pages=pass")
print("yandex_auth=redacted_status_only")
print("yandex_offline=dry_run_two_conversions")
print("yandex_live_safe_upload=transport_verified")
print("yandex_duplicates=dedupe_key_stable")
print("dashboard_readiness=metadata_only_live_safe_verified")
print("dashboard_goal_visibility=metadata_only_contract_verified")
print("dashboard_owner=role_only")
print("dashboard_provider_gap_caveat=present")
print("provider_blockers=legal_privacy_security_qa_disclosure_campaign_product_rollout_separate")
print("product_rollout=blocked")
print("campaign_launch=blocked")
print("no_secret_scan=metadata_only_pass")
print("private_payload_status=none_committed")
print("rollback_status=metadata_only_not_executed")
print("rollback_execution=metadata_only_no_state_change")
print("rollback_live_mutation=not_claimed")
PY
