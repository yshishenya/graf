#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: rollback-product-analytics-providers.sh [--metadata-only|--dry-run|--execute] [--target <target>]

--metadata-only (default) prints the redacted rollback contract without changing
provider state. --dry-run is a compatibility alias.

--execute is fail-closed: it requires
TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE=1 and an absolute executable operator
hook in TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK. The hook receives
--target <target> and owns any live provider mutation.
EOF
}

target="all"
mode="metadata_only"
mode_set=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ] || [[ "${2:-}" == --* ]]; then
        echo "provider_rollback_result=blocked"
        echo "rollback_execution=argument_error"
        echo "rollback_blocker=missing_target"
        usage
        exit 2
      fi
      target="$2"
      shift 2
      ;;
    --metadata-only|--dry-run)
      if [ "$mode_set" = "1" ] && [ "$mode" != "metadata_only" ]; then
        echo "provider_rollback_result=blocked"
        echo "rollback_execution=argument_error"
        echo "rollback_blocker=conflicting_modes"
        exit 2
      fi
      mode="metadata_only"
      mode_set=1
      shift
      ;;
    --execute)
      if [ "$mode_set" = "1" ] && [ "$mode" != "execute" ]; then
        echo "provider_rollback_result=blocked"
        echo "rollback_execution=argument_error"
        echo "rollback_blocker=conflicting_modes"
        exit 2
      fi
      mode="execute"
      mode_set=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "provider_rollback_result=blocked"
      echo "rollback_execution=argument_error"
      echo "rollback_blocker=unknown_argument"
      usage
      exit 2
      ;;
  esac
done

case "$target" in
  all|posthog_delivery|posthog_autocapture|posthog_stack|yandex|yandex_offline|validation)
    ;;
  *)
    echo "provider_rollback_result=blocked"
    echo "rollback_execution=argument_error"
    echo "rollback_blocker=unknown_target"
    exit 2
    ;;
esac

print_blocked() {
  local blocker="$1"
  local execution="${2:-execute_blocked}"
  echo "provider_rollback_result=blocked"
  echo "rollback_execution=$execution"
  echo "rollback_blocker=$blocker"
  echo "target=$target"
  echo "operator_executor_hook=not_invoked"
  echo "product_impact=measurement_gap_only"
  echo "normal_product_workflows=preserved"
  echo "secrets=not_printed"
}

if [ "$mode" = "execute" ]; then
  executor_hook="${TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK:-}"

  if [ "${TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE:-}" != "1" ]; then
    print_blocked "missing_explicit_execute_approval"
    exit 3
  fi
  if [ -z "$executor_hook" ]; then
    print_blocked "missing_operator_executor_hook"
    exit 3
  fi
  if [[ "$executor_hook" != /* ]]; then
    print_blocked "operator_executor_hook_must_be_absolute"
    exit 3
  fi
  if [ ! -f "$executor_hook" ] || [ ! -x "$executor_hook" ]; then
    print_blocked "operator_executor_hook_not_executable"
    exit 3
  fi

  # The hook is the explicit operator-owned mutation boundary. Suppress its
  # output so provider secrets or payloads cannot leak through this metadata
  # contract; a non-zero hook status remains a fail-closed blocker.
  if ! "$executor_hook" --target "$target" >/dev/null 2>&1; then
    print_blocked "operator_executor_hook_failed" "execute_hook_failed"
    exit 4
  fi
  execution="executed_via_operator_hook"
  state_mutation="delegated_to_operator_hook"
  hook_status="configured_redacted_invoked"
  stack_stop="delegated_to_operator_hook"
else
  execution="metadata_only_no_state_change"
  state_mutation="not_requested"
  hook_status="not_invoked"
  stack_stop="metadata_only_no_state_change"
fi

cat <<EOF
provider_rollback_result=pass
rollback_execution=$execution
target=$target
provider_state_mutation=$state_mutation
operator_executor_hook=$hook_status
product_impact=measurement_gap_only
posthog_delivery_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false
posthog_web_direct_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED=false
posthog_desktop_direct_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED=false
posthog_autocapture_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED=false
posthog_replay_switch=TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=false
posthog_stack_stop=$stack_stop
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
