#!/usr/bin/env sh
set -eu

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
trigger="unspecified"
prior_state_reference="${TWOBRAIN_PRIOR_STATE_REFERENCE:-}"
residue_owner="${TWOBRAIN_RESIDUE_OWNER:-deployment-operator}"
residue_follow_up_reason="${TWOBRAIN_RESIDUE_FOLLOW_UP_REASON:-recorded-before-retry}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --remote)
      exec ssh "$host" "cd '$path' && ./infra/scripts/rollback-rec-stack.sh --execute --trigger '$trigger'"
      ;;
    --execute)
      execute=1
      shift
      ;;
    --dry-run)
      execute=0
      shift
      ;;
    --trigger)
      trigger="${2:-unspecified}"
      shift 2
      ;;
    --prior-state-reference)
      prior_state_reference="${2:-}"
      shift 2
      ;;
    --residue-owner)
      residue_owner="${2:-deployment-operator}"
      shift 2
      ;;
    --residue-follow-up-reason)
      residue_follow_up_reason="${2:-recorded-before-retry}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

case "$trigger" in
  dns_tls|secrets|health|storage|disk_full|unsafe_exposure|forbidden_content)
    decision="halt"
    ;;
  migration)
    decision="restore"
    ;;
  smoke_upload)
    decision="rollback"
    ;;
  backup|restore_rehearsal|cleanup)
    decision="blocked"
    ;;
  *)
    decision="halt"
    ;;
esac

case "$decision" in
  restore|rollback)
    if [ -z "$prior_state_reference" ]; then
      prior_state_reference="required-before-execute"
    fi
    ;;
esac

if [ "${execute:-0}" != "1" ]; then
  cat <<EOF
rollback_decision=$decision
trigger=$trigger
remote_host=$host
deploy_path=$path
prior_state_reference=$prior_state_reference
cleanup_obligations=record_any_residue_before_retry
residue_owner=$residue_owner
residue_follow_up_reason=$residue_follow_up_reason
EOF
  exit 0
fi

docker compose -f infra/docker-compose.yml ps
cat <<EOF
rollback_decision=$decision
trigger=$trigger
remote_host=$host
deploy_path=$path
prior_state_reference=$prior_state_reference
cleanup_obligations=record_any_residue_before_retry
residue_owner=$residue_owner
residue_follow_up_reason=$residue_follow_up_reason
EOF
