#!/usr/bin/env bash
set -euo pipefail

branch="${1:?branch is required}"
expected_sha="${2:?expected sha is required}"
previous_sha="${3:?previous sha is required}"
compose=(docker compose -f infra/docker-compose.yml)
runtime_mutated=0
deployment_complete=0
dispatch_opened=0
previous_schema_head=""
expected_schema_head=""

set -a
. ./.env
set +a

# File-backed Compose secrets retain host ownership. Keep generated files in
# the deploy user's private primary group and grant only that numeric group to
# the non-root services that consume them.
runtime_secret_gid="${TWOBRAIN_RUNTIME_SECRET_GID:-1001}"

validate_runtime_secret_group() {
  local current_gid current_user group_record group_members primary_account_count
  if [[ ! "$runtime_secret_gid" =~ ^[1-9][0-9]{3,9}$ ]] \
    || (( runtime_secret_gid > 2147483647 )); then
    return 1
  fi
  current_gid="$(id -g)"
  current_user="$(id -un)"
  if [[ "$current_gid" != "$runtime_secret_gid" ]]; then
    return 1
  fi
  group_record="$(getent group "$runtime_secret_gid" 2>/dev/null || true)"
  if [[ -z "$group_record" ]]; then
    return 1
  fi
  group_members="${group_record##*:}"
  if [[ -n "$group_members" && "$group_members" != "$current_user" ]]; then
    return 1
  fi
  primary_account_count="$(
    getent passwd | awk -F: -v gid="$runtime_secret_gid" \
      '$4 == gid {count++} END {print count + 0}'
  )"
  [[ "$primary_account_count" == "1" ]]
}

secure_generated_secret() {
  local target="$1" initial_facts expected_facts actual_facts
  if [[ -L "$target" || ! -f "$target" || ! -s "$target" ]]; then
    return 1
  fi
  initial_facts="$(stat -c '%u:%h' -- "$target" 2>/dev/null)" || return 1
  if [[ "$initial_facts" != "$(id -u):1" ]]; then
    return 1
  fi
  chgrp "$runtime_secret_gid" -- "$target" 2>/dev/null || return 1
  chmod 640 -- "$target" 2>/dev/null || return 1
  expected_facts="$(id -u):${runtime_secret_gid}:640:1"
  actual_facts="$(stat -c '%u:%g:%a:%h' -- "$target" 2>/dev/null)" || return 1
  [[ "$actual_facts" == "$expected_facts" ]]
}

ensure_generated_secret() {
  local target="$1"
  local byte_count="$2"
  if [[ -L "$target" || ( -e "$target" && ! -f "$target" ) ]]; then
    echo "deploy_result=blocked"
    echo "reason=generated_secret_path_invalid"
    exit 1
  fi
  if [[ -s "$target" ]]; then
    if ! secure_generated_secret "$target"; then
      echo "deploy_result=blocked"
      echo "reason=generated_secret_permissions_invalid"
      exit 1
    fi
    return
  fi
  local directory
  directory="$(dirname "$target")"
  if [[ -L "$directory" || ( -e "$directory" && ! -d "$directory" ) ]]; then
    echo "deploy_result=blocked"
    echo "reason=generated_secret_directory_invalid"
    exit 1
  fi
  local prior_umask temporary
  prior_umask="$(umask)"
  umask 077
  mkdir -p "$directory"
  temporary="$(mktemp "${target}.tmp.XXXXXX")"
  openssl rand -hex "$byte_count" >"$temporary"
  chmod 600 "$temporary"
  mv "$temporary" "$target"
  umask "$prior_umask"
  if ! secure_generated_secret "$target"; then
    echo "deploy_result=blocked"
    echo "reason=generated_secret_permissions_invalid"
    exit 1
  fi
}

cleanup_runtime_files() {
  rm -f \
    /tmp/twobrain-rec-api-env.txt \
    /tmp/twobrain-rec-compose-deploy.yml \
    /tmp/twobrain-rec-media-worker-env.txt
}

verify_api_dispatch_gate() {
  local expected_capability="$1"
  local expected_dispatch="$2"
  local api_container
  api_container="$("${compose[@]}" ps -q rec-api)"
  if [[ -z "$api_container" ]]; then
    return 1
  fi
  docker inspect "$api_container" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    >/tmp/twobrain-rec-api-env.txt
  grep -Fxq "TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=$expected_capability" \
    /tmp/twobrain-rec-api-env.txt \
    && grep -Fxq \
      "TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=$expected_dispatch" \
      /tmp/twobrain-rec-api-env.txt
}

rollback_feature_storage() {
  local root_user_file root_password_file media_access_file
  root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
  root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
  media_access_file="${TWOBRAIN_MINIO_MEDIA_ACCESS_KEY_FILE:-./secrets/twobrain_minio_media_access_key}"
  docker run --rm \
    --network twobrain-rec-private \
    --entrypoint /bin/sh \
    -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
    -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
    -v "$media_access_file":/run/secrets/twobrain_minio_media_access_key:ro \
    minio/mc:RELEASE.2025-05-21T01-59-54Z \
    -eu -c '
      mc alias set rec http://rec-minio:9000 \
        "$(cat /run/secrets/twobrain_minio_root_user)" \
        "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null
      mc admin user rm rec "$(cat /run/secrets/twobrain_minio_media_access_key)" >/dev/null 2>&1 || true
      mc admin policy rm rec twobrain-rec-media >/dev/null 2>&1 || true
    '
}

rollback_feature_database() {
  "${compose[@]}" run --rm --no-deps rec-migrate \
    alembic downgrade "$previous_schema_head"
  local role_name role_exists
  for role_name in twobrain_rec_app twobrain_rec_media twobrain_rec_maintenance; do
    role_exists="$("${compose[@]}" exec -T rec-postgres psql \
      -U twobrain_rec \
      -d twobrain_rec \
      -Atc "select 1 from pg_roles where rolname = '$role_name'" \
      | tr -d '\r')"
    if [[ "$role_exists" != "1" ]]; then
      continue
    fi
    "${compose[@]}" exec -T rec-postgres psql \
      -v ON_ERROR_STOP=1 \
      -U twobrain_rec \
      -d twobrain_rec <<SQL
select pg_terminate_backend(pid)
from pg_stat_activity
where usename = '$role_name'
  and pid <> pg_backend_pid();
drop owned by $role_name;
drop role $role_name;
SQL
  done
}

feature_truth_count() {
  local tables_present
  tables_present="$("${compose[@]}" exec -T rec-postgres psql \
    -U twobrain_rec \
    -d twobrain_rec \
    -Atc "select count(*) from (values
      (to_regclass('public.playback_backfill_runs')),
      (to_regclass('public.playback_normalization_jobs')),
      (to_regclass('public.playback_normalization_attempts'))
    ) as feature_tables(name) where name is not null" \
    | tr -d '\r')"
  if [[ "$tables_present" == "0" ]]; then
    printf '0\n'
    return
  fi
  if [[ "$tables_present" != "3" ]]; then
    return 1
  fi
  "${compose[@]}" exec -T rec-postgres psql \
    -U twobrain_rec \
    -d twobrain_rec \
    -Atc "select
      (select count(*) from playback_backfill_runs)
      + (select count(*) from playback_normalization_jobs)
      + (select count(*) from playback_normalization_attempts)
      + (select count(*) from track_artifacts
          where normalization_profile_version =
            'review_m4a_aac_lc_48k_mono_64k_v1')" \
    | tr -d '\r'
}

restore_previous_services() {
  local rollback_failed=0
  git reset --hard "$previous_sha" >/dev/null 2>&1 || rollback_failed=1
  local available_services rollback_build_services rollback_up_services service
  available_services="$("${compose[@]}" config --services 2>/dev/null || true)"
  rollback_build_services=()
  rollback_up_services=()
  for service in rec-api rec-db-runtime-bootstrap rec-maintenance rec-reprocess-maintenance rec-migrate rec-minio-init rec-processing-worker; do
    if grep -Fxq "$service" <<<"$available_services"; then
      rollback_build_services+=("$service")
    fi
  done
  for service in rec-api rec-migrate rec-minio rec-minio-init rec-temporal rec-processing-worker; do
    if grep -Fxq "$service" <<<"$available_services"; then
      rollback_up_services+=("$service")
    fi
  done
  if (( ${#rollback_build_services[@]} == 0 || ${#rollback_up_services[@]} == 0 )); then
    rollback_failed=1
  else
    "${compose[@]}" build "${rollback_build_services[@]}" || rollback_failed=1
    "${compose[@]}" up -d --no-build --wait --wait-timeout 240 \
      "${rollback_up_services[@]}" || rollback_failed=1
  fi
  return "$rollback_failed"
}

restore_compatibility_runtime() {
  local rollback_failed=0
  TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=false \
    TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=false \
    "${compose[@]}" up -d --no-deps --no-build --force-recreate \
    --wait --wait-timeout 240 rec-api >/dev/null 2>&1 || rollback_failed=1
  verify_api_dispatch_gate false false || rollback_failed=1
  if [[ "$rollback_failed" == "0" ]]; then
    echo "rollback_result=pass"
    echo "rollback_target=compatibility_099"
    echo "rollback_runtime_sha=$expected_sha"
    echo "dispatch_stopped=true"
    echo "legacy_playback_guard_retained=true"
  else
    echo "rollback_result=blocked"
    echo "rollback_target=forward_fix_required"
    echo "rollback_backup_reference=${backup_reference:-unavailable}"
  fi
  return "$rollback_failed"
}

restore_previous_runtime() {
  local rollback_failed=0 media_container current_schema truth_count
  echo "rollback_result=started"
  media_container="$("${compose[@]}" ps -q rec-media-worker 2>/dev/null || true)"
  "${compose[@]}" stop rec-media-worker rec-api >/dev/null 2>&1 || true
  [[ -z "$media_container" ]] || docker rm -f "$media_container" >/dev/null 2>&1 || true
  current_schema="$("${compose[@]}" exec -T rec-postgres psql \
    -U twobrain_rec -d twobrain_rec -Atc 'select version_num from alembic_version' \
    2>/dev/null | tr -d '\r' || true)"
  truth_count="$(feature_truth_count 2>/dev/null || printf 'unknown\n')"

  if [[ "$dispatch_opened" == "0" \
    && "$previous_schema_head" != "$expected_schema_head" \
    && ( "$current_schema" == "$previous_schema_head" \
      || "$current_schema" == "$expected_schema_head" ) \
    && "$truth_count" == "0" ]]; then
    if [[ "$current_schema" == "$expected_schema_head" ]]; then
      rollback_feature_database || rollback_failed=1
    fi
    rollback_feature_storage || rollback_failed=1
    restore_previous_services || rollback_failed=1
    if [[ "$rollback_failed" == "0" ]]; then
      echo "rollback_result=pass"
      echo "rollback_target=raw_pre_099_without_feature_truth"
      echo "rollback_runtime_sha=$previous_sha"
      echo "dispatch_stopped=true"
      echo "feature_truth_count=0"
    else
      echo "rollback_result=blocked"
      echo "rollback_target=forward_fix_required"
      echo "rollback_backup_reference=${backup_reference:-unavailable}"
    fi
    return
  fi
  restore_compatibility_runtime || true
}

rollback_on_exit() {
  local status=$?
  trap - EXIT INT TERM
  if [[ "$status" == "0" || "$deployment_complete" == "1" ]]; then
    return
  fi
  set +e
  echo "deploy_result=blocked"
  echo "reason=staged_rollout_failed"
  if [[ "$runtime_mutated" == "1" ]]; then
    restore_previous_runtime
  else
    if git reset --hard "$previous_sha" >/dev/null 2>&1; then
      echo "rollback_result=source_restored"
      echo "rollback_runtime_sha=$previous_sha"
    else
      echo "rollback_result=blocked"
      echo "rollback_backup_reference=${backup_reference:-unavailable}"
    fi
  fi
  cleanup_runtime_files
  exit "$status"
}
trap rollback_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! validate_runtime_secret_group; then
  echo "deploy_result=blocked"
  echo "reason=runtime_secret_group_unsafe"
  exit 1
fi
export TWOBRAIN_RUNTIME_SECRET_GID="$runtime_secret_gid"
echo "runtime_secret_group_result=pass"

ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_APP_PASSWORD_FILE:-./secrets/twobrain_postgres_app_password}" 32
ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_MAINTENANCE_PASSWORD_FILE:-./secrets/twobrain_postgres_maintenance_password}" 32
ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_MEDIA_PASSWORD_FILE:-./secrets/twobrain_postgres_media_password}" 32
echo "runtime_db_secret_provision_result=pass"
ensure_generated_secret \
  "${TWOBRAIN_MINIO_MEDIA_ACCESS_KEY_FILE:-./secrets/twobrain_minio_media_access_key}" 10
ensure_generated_secret \
  "${TWOBRAIN_MINIO_MEDIA_SECRET_KEY_FILE:-./secrets/twobrain_minio_media_secret_key}" 32
echo "media_storage_secret_provision_result=pass"

backup_output="$(infra/scripts/backup-rec-stack.sh --execute)"
printf '%s\n' "$backup_output"
backup_reference="$(printf '%s\n' "$backup_output" | sed -n 's/^backup_reference=//p' | tail -n 1)"
if [[ -z "$backup_reference" ]]; then
  echo "deploy_result=blocked"
  echo "reason=backup_reference_missing"
  exit 1
fi
RESTORE_BACKUP_REFERENCE="$backup_reference" infra/scripts/rehearse-rec-restore.sh --execute

"${compose[@]}" config >/tmp/twobrain-rec-compose-deploy.yml
if grep -Eq 'TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY|MINIO_MEDIA_ACCESS_KEY|MINIO_MEDIA_SECRET_KEY|POSTAL_API_KEY|WEB_CSRF_SECRET):|MINIO_ROOT_PASSWORD:|MINIO_ROOT_USER:|POSTGRES_PWD:' /tmp/twobrain-rec-compose-deploy.yml; then
  echo "deploy_result=blocked"
  echo "reason=secret_env_exposure"
  exit 1
fi

previous_schema_head="$("${compose[@]}" exec -T rec-postgres psql \
  -U twobrain_rec -d twobrain_rec -Atc 'select version_num from alembic_version' | tr -d '\r')"
if [[ ! "$previous_schema_head" =~ ^[0-9A-Za-z_]+$ ]]; then
  echo "deploy_result=blocked"
  echo "reason=previous_schema_head_unavailable"
  exit 1
fi

"${compose[@]}" build \
  rec-api \
  rec-db-runtime-bootstrap \
  rec-maintenance \
  rec-reprocess-maintenance \
  rec-migrate \
  rec-minio-init \
  rec-processing-worker \
  rec-media-worker

media_image_ref="$(
  "${compose[@]}" config --images |
    awk '$0 ~ /(^|[-_])rec-media-worker(:[^[:space:]]+)?$/ {image=$0} END {if (image != "") print image}'
)"
media_image=""
if [[ -n "$media_image_ref" ]]; then
  media_image="$(docker image inspect "$media_image_ref" --format '{{.Id}}' 2>/dev/null || true)"
fi
if [[ -z "$media_image" ]]; then
  echo "deploy_result=blocked"
  echo "reason=media_worker_image_missing"
  exit 1
fi
expected_schema_head="$(docker run --rm --network none --read-only "$media_image" \
  python -c 'from twobrain_rec_server.normalization.worker import packaged_schema_head; print(packaged_schema_head())')"
if [[ ! "$expected_schema_head" =~ ^[0-9A-Za-z_]+$ ]]; then
  echo "deploy_result=blocked"
  echo "reason=packaged_schema_head_unavailable"
  exit 1
fi
capability_receipt="$(docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --pids-limit 128 \
  --memory 1g \
  --cpus 1 \
  --tmpfs /var/lib/twobrain-rec/playback-normalization:rw,noexec,nosuid,nodev,size=512m,mode=0700,uid=100,gid=101 \
  "$media_image" \
  python /app/scripts/verify_playback_normalization_runtime.py)"
if ! grep -Fq '"synthetic_residue_count":0' <<<"$capability_receipt"; then
  echo "deploy_result=blocked"
  echo "reason=image_capability_cleanup_failed"
  exit 1
fi
if ! grep -Fq '"profile_version":"review_m4a_aac_lc_48k_mono_64k_v1"' \
    <<<"$capability_receipt" \
  || ! grep -Fq '"validation_version":"playback_validator_v1"' \
    <<<"$capability_receipt"; then
  echo "deploy_result=blocked"
  echo "reason=profile_contract_mismatch"
  exit 1
fi
echo "image_capability_result=pass"
echo "profile_contract_result=pass"

runtime_mutated=1
"${compose[@]}" stop rec-media-worker >/dev/null 2>&1 || true
TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=false \
  TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=false \
  "${compose[@]}" up -d --no-build --wait --wait-timeout 240 \
  rec-api \
  rec-migrate \
  rec-minio \
  rec-minio-init \
  rec-temporal \
  rec-processing-worker

if ! verify_api_dispatch_gate false false; then
  echo "deploy_result=blocked"
  echo "reason=initial_dispatch_gate_not_closed"
  exit 1
fi
echo "initial_dispatch_gate_result=closed"

role_bootstrap_output="$("${compose[@]}" run --rm --no-deps rec-db-runtime-bootstrap)"
if ! grep -Fxq 'runtime_database_roles_result=pass' <<<"$role_bootstrap_output"; then
  echo "deploy_result=blocked"
  echo "reason=runtime_db_role_bootstrap_failed"
  exit 1
fi
echo "runtime_db_role_bootstrap_result=pass"

migration_output="$("${compose[@]}" run --rm --no-deps rec-migrate alembic current)"
if ! grep -Fq "$expected_schema_head" <<<"$migration_output" \
  || ! grep -Fq 'head' <<<"$migration_output"; then
  echo "deploy_result=blocked"
  echo "reason=migration_head_not_current"
  exit 1
fi
echo "migration_head_result=pass"
echo "migration_head=$expected_schema_head"

api_database_identity="$("${compose[@]}" exec -T \
  -e TWOBRAIN_EXPECTED_DATABASE_ROLE=twobrain_rec_app \
  rec-api python /app/scripts/verify_runtime_database_identity.py)"
if ! grep -Fxq 'runtime_database_identity_result=pass' <<<"$api_database_identity" \
  || ! grep -Fxq 'runtime_database_role=twobrain_rec_app' <<<"$api_database_identity" \
  || ! grep -Fxq 'scheduler_function_access=denied' <<<"$api_database_identity" \
  || ! grep -Fxq 'legacy_maintenance_access=denied' <<<"$api_database_identity"; then
  echo "deploy_result=blocked"
  echo "reason=api_runtime_database_identity_failed"
  exit 1
fi
echo "api_runtime_database_identity_result=pass"

maintenance_database_identity="$("${compose[@]}" run --rm --no-deps -T \
  -e TWOBRAIN_EXPECTED_DATABASE_ROLE=twobrain_rec_maintenance \
  rec-maintenance python /app/scripts/verify_runtime_database_identity.py)"
if ! grep -Fxq 'runtime_database_identity_result=pass' <<<"$maintenance_database_identity" \
  || ! grep -Fxq 'runtime_database_role=twobrain_rec_maintenance' \
    <<<"$maintenance_database_identity" \
  || ! grep -Fxq 'scheduler_function_access=denied' <<<"$maintenance_database_identity" \
  || ! grep -Fxq 'legacy_maintenance_access=allowed' <<<"$maintenance_database_identity"; then
  echo "deploy_result=blocked"
  echo "reason=maintenance_runtime_database_identity_failed"
  exit 1
fi
echo "maintenance_runtime_database_identity_result=pass"

verify_media_worker_boundary() {
  local expected_dispatch="$1"
  local media_worker_container media_networks
  media_worker_container="$("${compose[@]}" ps -q rec-media-worker)"
  if [[ -z "$media_worker_container" \
    || "$(docker inspect "$media_worker_container" --format '{{.State.Status}}')" != "running" \
    || "$(docker inspect "$media_worker_container" --format '{{.State.Health.Status}}')" != "healthy" \
    || "$(docker inspect "$media_worker_container" --format '{{.Config.User}}')" != "twobrain" \
    || "$(docker inspect "$media_worker_container" --format '{{json .HostConfig.GroupAdd}}')" != "[\"$runtime_secret_gid\"]" \
    || "$(docker inspect "$media_worker_container" --format '{{.HostConfig.ReadonlyRootfs}}')" != "true" \
    || "$(docker inspect "$media_worker_container" --format '{{.HostConfig.NanoCpus}}')" != "1000000000" \
    || "$(docker inspect "$media_worker_container" --format '{{.HostConfig.Memory}}')" != "1073741824" \
    || "$(docker inspect "$media_worker_container" --format '{{.HostConfig.PidsLimit}}')" != "128" \
    || "$(docker inspect "$media_worker_container" --format '{{json .HostConfig.CapDrop}}')" != '["ALL"]' \
    || "$(docker inspect "$media_worker_container" --format '{{json .HostConfig.SecurityOpt}}')" != '["no-new-privileges:true"]' ]]; then
    echo "deploy_result=blocked"
    echo "reason=media_worker_runtime_boundary_failed"
    exit 1
  fi
  media_networks="$(docker inspect "$media_worker_container" --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}')"
  if [[ "$(sed '/^$/d' <<<"$media_networks" | wc -l | tr -d ' ')" != "1" ]] \
    || ! grep -Fxq 'twobrain-rec-media-private' <<<"$media_networks"; then
    echo "deploy_result=blocked"
    echo "reason=media_worker_network_boundary_failed"
    exit 1
  fi
  docker inspect "$media_worker_container" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    >/tmp/twobrain-rec-media-worker-env.txt
  if ! grep -Fxq 'TWOBRAIN_PLAYBACK_NORMALIZATION_TASK_QUEUE=twobrain-rec-playback-normalization' \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fxq 'TWOBRAIN_PLAYBACK_NORMALIZATION_WORKER_CONCURRENCY=1' \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fxq "TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=$expected_dispatch" \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fxq 'TWOBRAIN_MINIO_ACCESS_KEY_FILE=/run/secrets/twobrain_minio_media_access_key' \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fxq 'TWOBRAIN_MINIO_SECRET_KEY_FILE=/run/secrets/twobrain_minio_media_secret_key' \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fxq 'TWOBRAIN_WEB_RUNTIME_ENABLED=false' \
      /tmp/twobrain-rec-media-worker-env.txt \
    || ! grep -Fq 'TWOBRAIN_DATABASE_URL=postgresql+asyncpg://twobrain_rec_media:' \
      /tmp/twobrain-rec-media-worker-env.txt; then
    echo "deploy_result=blocked"
    echo "reason=media_worker_dispatch_contract_failed"
    exit 1
  fi
}

verify_media_worker_control() {
  local media_database_identity control_receipt
  media_database_identity="$("${compose[@]}" exec -T \
    -e TWOBRAIN_EXPECTED_DATABASE_ROLE=twobrain_rec_media \
    rec-media-worker python /app/scripts/verify_runtime_database_identity.py)"
  if ! grep -Fxq 'runtime_database_identity_result=pass' <<<"$media_database_identity" \
    || ! grep -Fxq 'runtime_database_role=twobrain_rec_media' <<<"$media_database_identity" \
    || ! grep -Fxq 'scheduler_function_access=allowed' <<<"$media_database_identity" \
    || ! grep -Fxq 'legacy_maintenance_access=denied' <<<"$media_database_identity"; then
    echo "deploy_result=blocked"
    echo "reason=media_runtime_database_identity_failed"
    exit 1
  fi
  control_receipt="$("${compose[@]}" exec -T rec-media-worker \
    python /app/scripts/verify_playback_normalization_worker_ready.py --control)"
  if ! grep -Fq '"result":"pass"' <<<"$control_receipt" \
    || ! grep -Fq '"mode":"control"' <<<"$control_receipt" \
    || ! grep -Fq '"workflow_poller":"ready"' <<<"$control_receipt" \
    || ! grep -Fq '"activity_poller":"ready"' <<<"$control_receipt"; then
    echo "deploy_result=blocked"
    echo "reason=media_worker_control_probe_failed"
    exit 1
  fi
}

TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=false \
  "${compose[@]}" up -d --no-build --force-recreate --wait --wait-timeout 240 \
  rec-media-worker
verify_media_worker_boundary false
verify_media_worker_control
echo "media_worker_pre_dispatch_result=pass"

infra/scripts/run-production-smoke.sh --execute

dispatch_opened=1
TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=true \
  "${compose[@]}" up -d --no-build --force-recreate --wait --wait-timeout 900 \
  rec-media-worker
verify_media_worker_boundary true
verify_media_worker_control
echo "media_runtime_database_identity_result=pass"
echo "media_worker_result=pass"

TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=true \
  TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=true \
  "${compose[@]}" up -d --no-deps --no-build --force-recreate --wait --wait-timeout 240 \
  rec-api
if ! verify_api_dispatch_gate true true; then
  echo "deploy_result=blocked"
  echo "reason=automatic_dispatch_gate_not_open"
  exit 1
fi
echo "automatic_dispatch_result=pass"

if grep -Eq '^(TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY|MINIO_MEDIA_ACCESS_KEY|MINIO_MEDIA_SECRET_KEY|POSTAL_API_KEY|WEB_CSRF_SECRET)|MINIO_ROOT_PASSWORD|MINIO_ROOT_USER)=' \
    /tmp/twobrain-rec-api-env.txt \
  || grep -Eq '^(TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY|MINIO_MEDIA_ACCESS_KEY|MINIO_MEDIA_SECRET_KEY|POSTAL_API_KEY|WEB_CSRF_SECRET|MEDIASCRIBE_API_KEY)|MINIO_ROOT_PASSWORD|MINIO_ROOT_USER)=' \
    /tmp/twobrain-rec-media-worker-env.txt; then
  echo "deploy_result=blocked"
  echo "reason=runtime_secret_env_exposure"
  exit 1
fi

curl -fsS https://rec.2brain.pro/api/v1/health/live >/dev/null
curl -fsS https://rec.2brain.pro/api/v1/health/ready >/dev/null

echo "automatic_retry_result=required_post_deploy"
echo "backfill_inventory_result=required_post_deploy"
echo "range_playback_result=required_post_deploy"
echo "normalization_cleanup_result=required_post_deploy"

deployment_complete=1
cleanup_runtime_files
trap - EXIT INT TERM
cat <<EOF
deploy_result=pass
branch=$branch
deployed_sha=$expected_sha
backup_reference=$backup_reference
readiness_verdict=infra_smoke_ready
playback_normalization_scope=worker_capability_only
runtime_sha=$expected_sha
EOF
