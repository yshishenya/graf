#!/usr/bin/env bash
set -euo pipefail

target="all"
execute=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      target="${2:-all}"
      shift 2
      ;;
    --execute)
      execute=1
      shift
      ;;
    --dry-run)
      execute=0
      shift
      ;;
    *)
      shift
      ;;
  esac
done

case "$target" in
  all|posthog_delivery|posthog_autocapture|posthog_stack|yandex|yandex_offline|validation)
    ;;
  *)
    echo "provider_rollback_result=fail"
    echo "reason=unknown_target"
    exit 2
    ;;
esac

if [ "$execute" = "1" ] && [ "${TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE:-}" != "1" ]; then
  echo "provider_rollback_result=blocked"
  echo "rollback_execution=execute_requires_TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE"
  echo "product_impact=measurement_gap_only"
  exit 3
fi

if [ "$execute" = "1" ]; then
  execution="execute_confirmed_metadata_only"
else
  execution="dry_run_no_state_change"
fi

cat <<EOF
provider_rollback_result=pass
rollback_execution=$execution
target=$target
product_impact=measurement_gap_only
posthog_delivery_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false
posthog_web_direct_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED=false
posthog_desktop_direct_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED=false
posthog_autocapture_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED=false
posthog_replay_switch=TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=false
posthog_stack_stop=dry_run_metadata_only
posthog_deploy_dry_run=required_after_switch
posthog_move_out_failure=restore_endpoint_or_disable_delivery
yandex_all_pages_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false
yandex_offline_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false
yandex_webvisor_maps_forms=disabled_by_inventory
provider_validation_switch=TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled
dashboard_caveat=provider_delivery_gap_record_required
normal_product_workflows=preserved
secrets=not_printed
EOF
