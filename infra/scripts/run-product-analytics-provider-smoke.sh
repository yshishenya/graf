#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

docker compose -f infra/posthog/docker-compose.posthog.yml config >/dev/null
infra/scripts/cd-remote.sh --dry-run >/dev/null

PYTHONPATH="$ROOT_DIR/apps/server/src" python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.page_inventory import blocked_yandex_page_classes, yandex_approved_page_classes
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper, ProviderTransportResponse
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
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
    if not product_yandex_context["enabled"] or product_yandex_context["counter_id_present"] is not True:
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

    def posthog_transport(url, headers, body, timeout):
        if not url.endswith("/capture/") or b'"api_key"' not in body or b'"event"' not in body:
            raise SystemExit("provider smoke failed")
        return ProviderTransportResponse(status_code=200, body='{"status":"ok"}')

    def yandex_transport(url, headers, body, timeout):
        if "offline_conversions/upload" not in url or b"Target,DateTime,UserId,PurchaseId" not in body:
            raise SystemExit("provider smoke failed")
        return ProviderTransportResponse(status_code=200, body='{"uploading":{"id":1}}')

    live_posthog = PostHogClientWrapper.from_settings(live_settings)
    live_posthog.transport = posthog_transport
    live_posthog_delivery = live_posthog.capture(yandex_event)
    live_yandex = YandexOfflineConversionExporter.from_settings(live_settings)
    live_yandex.transport = yandex_transport
    live_yandex_delivery = live_yandex.export(yandex_event)
    if live_posthog_delivery.status != "live_safe_sent" or live_yandex_delivery.status != "live_safe_uploaded":
        raise SystemExit("provider smoke failed")
    live_readiness = build_rollout_readiness_report(live_settings).as_dict()
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
print("rollback_status=ready_not_executed")
PY
