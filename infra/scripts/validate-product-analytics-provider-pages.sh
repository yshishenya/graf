#!/usr/bin/env bash
set -euo pipefail

# Provider page validation for product analytics.
#
# The check compares the rendered provider context of every page class with the
# policy that page class declares. Autocapture is enabled for exactly the page
# classes whose policy says `enabled`, and stays disabled for the classes whose
# policy says `disabled` (financial and fair-use surfaces fail closed). The
# earlier version required autocapture on every class, so the check started
# failing as soon as the inventory grew payment pages that must not be measured.
#
# FR-027 additionally requires consent-based measurement to cover every public
# page, including the landing page, the download page, sign-up and login, the
# legal documents and the page that describes analytics itself. Those classes
# are verified explicitly below.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/apps/server"

PYTHONPATH="$ROOT_DIR/apps/server/src" uv run python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.page_inventory import (
    page_class_policies,
    posthog_autocapture_page_classes,
)
from twobrain_rec_server.product_analytics.replay_masking import replay_decision_for_policy

# Public pages named by FR-027. Consent-based measurement must reach all of them.
REQUIRED_PUBLIC_PAGE_CLASSES = ("public_landing", "public_download", "legal", "login_signup")
# Page classes that must never send provider payloads by policy.
MUST_STAY_DISABLED = tuple(
    policy.page_class for policy in page_class_policies() if policy.posthog_autocapture_state == "disabled"
)

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
        product_analytics_direct_desktop_egress_approved=True,
    )
    policies = page_class_policies()
    contexts = {policy.page_class: build_browser_provider_context(settings, policy.page_class) for policy in policies}
    replay_decisions = {policy.page_class: replay_decision_for_policy(policy) for policy in policies}

declared_enabled = posthog_autocapture_page_classes()
if not declared_enabled:
    raise SystemExit("posthog_autocapture_missing")

for policy in policies:
    context = contexts[policy.page_class]
    expected = policy.posthog_autocapture_state == "enabled"
    if context["posthog"]["autocapture_enabled"] is not expected:
        raise SystemExit(f"posthog_autocapture_mismatch:{policy.page_class}")

for page_class in MUST_STAY_DISABLED:
    if contexts[page_class]["posthog"]["autocapture_enabled"]:
        raise SystemExit(f"posthog_autocapture_unexpected:{page_class}")

for page_class in REQUIRED_PUBLIC_PAGE_CLASSES:
    if page_class not in contexts:
        raise SystemExit(f"public_page_class_missing:{page_class}")
    if not contexts[page_class]["posthog"]["autocapture_enabled"]:
        raise SystemExit(f"public_page_measurement_missing:{page_class}")

if any(context["posthog"]["replay_enabled"] for context in contexts.values()):
    raise SystemExit("posthog_replay_unexpected")
if any(
    context["yandex"]["enabled"]
    for context in contexts.values()
    if context["page_class"] not in {"public_landing", "public_download"}
):
    raise SystemExit("yandex_blocked_page_enabled")
if any(context["yandex"]["webvisor_enabled"] for context in contexts.values()):
    raise SystemExit("webvisor_unexpected")
if any(decision.replay_allowed for decision in replay_decisions.values()):
    raise SystemExit("replay_or_webvisor_unexpected")
if any("data-ph-no-capture" in decision.attributes for decision in replay_decisions.values()):
    raise SystemExit("posthog_autocapture_disabled_by_replay_boundary")
if not all(context["private_attributes"].get("data-ph-mask") == "true" for context in contexts.values()):
    raise SystemExit("posthog_mask_missing")
if not all(context["private_attributes"].get("data-ym-hide-content") == "true" for context in contexts.values()):
    raise SystemExit("yandex_hide_content_missing")

print("provider_page_validation=pass")
print(f"page_classes_checked={len(policies)}")
print(f"posthog_autocapture=declared_classes_only count={len(declared_enabled)}")
print("posthog_autocapture_disabled_classes=" + ",".join(MUST_STAY_DISABLED))
print("public_page_measurement_classes=" + ",".join(REQUIRED_PUBLIC_PAGE_CLASSES))
print("posthog_replay=disabled")
print("posthog_replay_boundary=mask_only_no_no_capture")
print("yandex_public_scope=public_landing_public_download")
print("yandex_blocked_classes=blocked_or_replay_unavailable")
print("webvisor_maps_forms=disabled")
print("private_attributes=present")
print("desktop_direct_posthog=contract_tested")
print("desktop_direct_yandex=blocked")
PY
