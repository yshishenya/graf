#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHONPATH="$ROOT_DIR/apps/server/src" python - <<'PY'
from twobrain_rec_server.product_analytics.page_inventory import (
    approved_provider_page_classes,
    blocked_page_classes,
    get_page_class_policy,
)

approved = approved_provider_page_classes()
blocked = blocked_page_classes()
cabinet = get_page_class_policy("cabinet_home")

assert approved == ("public_landing", "public_download")
assert "admin" in blocked
assert "auth_callback" in blocked
assert cabinet.launch_state == "replay_unavailable"
assert not cabinet.posthog_replay_allowed
assert not cabinet.yandex_webvisor_allowed

print("product_analytics_page_scope=pass")
print("approved=" + ",".join(approved))
print("blocked=" + ",".join(blocked))
PY
