#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHONPATH="$ROOT_DIR/apps/server/src" python - <<'PY'
from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService

identity = build_safe_identity(user_source_id="smoke-094")
service = ProductAnalyticsIngestService(
    Settings(product_analytics_enabled=True, product_analytics_validation_mode="render_only")
)
result = service.ingest({
    "event_name": "desktop_first_opened",
    "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
    "properties": {
        "platform": "macos",
        "bridge_present": True,
        "install_channel": "smoke",
    },
})
if not result.accepted:
    raise SystemExit("product analytics smoke was not accepted")
print("product_analytics_smoke=pass")
print("provider_statuses=" + ",".join(item.status for item in result.provider_results))
PY
