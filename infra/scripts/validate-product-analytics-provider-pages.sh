#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/apps/server"

PYTHONPATH="$ROOT_DIR/apps/server/src" uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.page_inventory import page_class_policies
from twobrain_rec_server.product_analytics.replay_masking import replay_decision_for_policy

with TemporaryDirectory() as tmpdir:
    key_file = Path(tmpdir) / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_provider_mode="parallel_measurement",
        product_analytics_validation_mode="provider_smoke",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key_file,
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_legal_approved=True,
        product_analytics_posthog_desktop_direct_enabled=True,
        product_analytics_direct_provider_egress_approved=True,
    )
    policies = page_class_policies()
    contexts = [build_browser_provider_context(settings, policy.page_class) for policy in policies]
    replay_decisions = [replay_decision_for_policy(policy) for policy in policies]

if not all(context["posthog"]["autocapture_enabled"] for context in contexts):
    raise SystemExit("posthog_autocapture_missing")
if any(context["posthog"]["replay_enabled"] for context in contexts):
    raise SystemExit("posthog_replay_unexpected")
if any(
    context["yandex"]["enabled"]
    for context in contexts
    if context["page_class"] not in {"public_landing", "public_download"}
):
    raise SystemExit("yandex_blocked_page_enabled")
if any(decision.replay_allowed for decision in replay_decisions):
    raise SystemExit("replay_or_webvisor_unexpected")
if any("data-ph-no-capture" in decision.attributes for decision in replay_decisions):
    raise SystemExit("posthog_autocapture_disabled_by_replay_boundary")
if not all(context["private_attributes"].get("data-ph-mask") == "true" for context in contexts):
    raise SystemExit("posthog_mask_missing")
if not all(context["private_attributes"].get("data-ym-hide-content") == "true" for context in contexts):
    raise SystemExit("yandex_hide_content_missing")

print("provider_page_validation=pass")
print("posthog_autocapture=current_and_future_pages_enabled")
print("posthog_replay=disabled")
print("posthog_replay_boundary=mask_only_no_no_capture")
print("yandex_public_scope=public_landing_public_download")
print("yandex_blocked_classes=blocked_or_replay_unavailable")
print("webvisor_maps_forms=disabled")
print("private_attributes=present")
print("desktop_direct_posthog=contract_tested")
print("desktop_direct_yandex=blocked")
PY
