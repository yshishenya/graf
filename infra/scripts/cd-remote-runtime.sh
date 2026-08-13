#!/usr/bin/env bash
set -euo pipefail

branch="${1:?branch is required}"
expected_sha="${2:?expected sha is required}"
previous_sha="${3:?previous sha is required}"
compose=(docker compose --profile operations -f infra/docker-compose.yml)
runtime_mutated=0
deployment_complete=0
dispatch_opened=0
previous_schema_head=""
expected_schema_head=""
temporal_container_baseline=""
temporal_restart_baseline=""
processing_worker_container_baseline=""
processing_worker_restart_baseline=""
maintenance_container_baseline=""
maintenance_restart_baseline=""
public_download_updated=0
public_download_source=""
public_download_target=""
public_download_backup=""
public_download_temporary=""
public_download_smoke_directory=""

set -a
. ./.env
set +a
export TWOBRAIN_LANGFUSE_RELEASE="$expected_sha"

repo_root="$(pwd -P)"
disabled_billing_secret="$repo_root/infra/secret-placeholders/disabled_optional_provider_secret"
normalize_compose_secret_path() {
  local value="$1"
  case "$value" in
    /*) printf '%s' "$value" ;;
    ./*) printf '%s/%s' "$repo_root" "${value#./}" ;;
    ../*) printf '%s/infra/%s' "$repo_root" "$value" ;;
    *) printf '%s/%s' "$repo_root" "$value" ;;
  esac
}
if [[ "${TWOBRAIN_BILLING_PROVIDER_OBSERVATION_ENABLED:-false}" == "true" \
  || "${TWOBRAIN_BILLING_CHECKOUT_ENABLED:-false}" == "true" ]]; then
  export TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE="$(
    normalize_compose_secret_path "${TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE:-./secrets/twobrain_yookassa_secret}"
  )"
else
  export TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE="$disabled_billing_secret"
fi
if [[ "${TWOBRAIN_BILLING_CHECKOUT_ENABLED:-false}" == "true" ]]; then
  export TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE="$(
    normalize_compose_secret_path "${TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE:-./secrets/twobrain_yookassa_webhook_secret}"
  )"
  export TWOBRAIN_BILLING_REFERRAL_SECRET_FILE="$(
    normalize_compose_secret_path "${TWOBRAIN_BILLING_REFERRAL_SECRET_FILE:-./secrets/twobrain_billing_referral_secret}"
  )"
else
  export TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE="$disabled_billing_secret"
  export TWOBRAIN_BILLING_REFERRAL_SECRET_FILE="$disabled_billing_secret"
fi

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

secure_runtime_secret_file() {
  local target="$1" initial_facts initial_access expected_facts actual_facts actual_access
  if [[ -L "$target" || ! -f "$target" || ! -s "$target" ]]; then
    return 1
  fi
  initial_facts="$(stat -c '%u:%h' -- "$target" 2>/dev/null)" || return 1
  if [[ "$initial_facts" != "$(id -u):1" ]]; then
    return 1
  fi
  # GNU ls exposes the extended-ACL marker that stat/find mode strings omit.
  # shellcheck disable=SC2012
  initial_access="$(LC_ALL=C ls -ldn -- "$target" 2>/dev/null | awk '{print $1}')" \
    || return 1
  if [[ "${#initial_access}" != "10" ]]; then
    return 1
  fi
  chgrp "$runtime_secret_gid" -- "$target" 2>/dev/null || return 1
  chmod 640 -- "$target" 2>/dev/null || return 1
  expected_facts="$(id -u):${runtime_secret_gid}:640:1"
  actual_facts="$(stat -c '%u:%g:%a:%h' -- "$target" 2>/dev/null)" || return 1
  # shellcheck disable=SC2012
  actual_access="$(LC_ALL=C ls -ldn -- "$target" 2>/dev/null | awk '{print $1}')" \
    || return 1
  [[ "$actual_facts" == "$expected_facts" && "$actual_access" == "-rw-r-----" ]]
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
    if ! secure_runtime_secret_file "$target"; then
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
  if ! secure_runtime_secret_file "$target"; then
    echo "deploy_result=blocked"
    echo "reason=generated_secret_permissions_invalid"
    exit 1
  fi
}

cleanup_runtime_files() {
  local cleanup_failed=0
  rm -f \
    /tmp/twobrain-rec-api-env.txt \
    /tmp/twobrain-rec-compose-deploy.yml \
    /tmp/twobrain-rec-media-worker-env.txt || cleanup_failed=1
  if [[ -n "$public_download_smoke_directory" \
    && -d "$public_download_smoke_directory" \
    && ! -L "$public_download_smoke_directory" ]]; then
    rm -f -- \
      "$public_download_smoke_directory/graf.pkg" \
      "$public_download_smoke_directory/headers" || cleanup_failed=1
    rmdir -- "$public_download_smoke_directory" 2>/dev/null || cleanup_failed=1
  fi
  return "$cleanup_failed"
}

restore_public_download() {
  local restore_failed=0
  if [[ -n "$public_download_temporary" && -e "$public_download_temporary" ]]; then
    rm -f -- "$public_download_temporary" || restore_failed=1
  fi
  if [[ "$public_download_updated" != "1" ]]; then
    if [[ -n "$public_download_backup" && -e "$public_download_backup" ]]; then
      rm -f -- "$public_download_backup" || restore_failed=1
    fi
    return "$restore_failed"
  fi
  if [[ -n "$public_download_backup" && -f "$public_download_backup" ]]; then
    mv "$public_download_backup" "$public_download_target" || restore_failed=1
  elif [[ -e "$public_download_target" ]]; then
    rm -f -- "$public_download_target" || restore_failed=1
  fi
  public_download_updated=0
  return "$restore_failed"
}

sync_public_download() {
  public_download_source="$repo_root/apps/server/src/twobrain_rec_server/public/static/public/downloads/graf.pkg"
  local runtime_dir="$repo_root/infra/runtime"
  local target_dir="$runtime_dir/public-downloads"
  public_download_target="$target_dir/graf.pkg"

  if [[ -L "$public_download_source" || ! -f "$public_download_source" || ! -s "$public_download_source" ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_source_invalid"
    exit 1
  fi
  if [[ -L "$runtime_dir" || ( -e "$runtime_dir" && ! -d "$runtime_dir" ) ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_runtime_directory_invalid"
    exit 1
  fi
  mkdir -p "$runtime_dir"
  if [[ "$(stat -c '%u' -- "$runtime_dir")" != "$(id -u)" \
    || -L "$target_dir" \
    || ( -e "$target_dir" && ! -d "$target_dir" ) ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_directory_invalid"
    exit 1
  fi
  mkdir -p "$target_dir"
  if [[ "$(stat -c '%u' -- "$target_dir")" != "$(id -u)" ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_directory_owner_invalid"
    exit 1
  fi
  if [[ -L "$public_download_target" || ( -e "$public_download_target" && ! -f "$public_download_target" ) ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_target_invalid"
    exit 1
  fi
  if [[ -f "$public_download_target" ]] && cmp -s "$public_download_source" "$public_download_target"; then
    echo "public_download_sync_result=unchanged"
    return
  fi

  public_download_temporary="$(mktemp "$target_dir/.graf.pkg.deploy.XXXXXX")"
  install -m 0644 "$public_download_source" "$public_download_temporary"
  cmp "$public_download_source" "$public_download_temporary"
  if [[ -f "$public_download_target" ]]; then
    public_download_backup="$(mktemp "$target_dir/.graf.pkg.rollback.XXXXXX")"
    cp -p "$public_download_target" "$public_download_backup"
    cmp "$public_download_target" "$public_download_backup"
  fi
  public_download_updated=1
  mv "$public_download_temporary" "$public_download_target"
  public_download_temporary=""
  cmp "$public_download_source" "$public_download_target"
  echo "public_download_sync_result=updated"
}

verify_public_download() {
  local base_url="${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}"
  local page package_path package_file headers_file expected_sha actual_sha
  local curl_options=(
    -fsS --connect-timeout 10 --max-time 90
    --retry 2 --retry-delay 1 --retry-all-errors
  )
  if ! page="$(curl "${curl_options[@]}" "$base_url/download")"; then
    echo "deploy_result=blocked"
    echo "reason=public_download_page_unavailable"
    exit 1
  fi
  if ! package_path="$(python3 -c '
import re
import sys

match = re.search(r"(/static/public/downloads/graf[.]pkg[?]v=[0-9a-f]{12})", sys.stdin.read())
if match is None:
    raise SystemExit(1)
print(match.group(1))
' <<<"$page")"; then
    echo "deploy_result=blocked"
    echo "reason=public_download_link_missing"
    exit 1
  fi
  public_download_smoke_directory="$(mktemp -d /tmp/graf-public-download.XXXXXX)"
  package_file="$public_download_smoke_directory/graf.pkg"
  headers_file="$public_download_smoke_directory/headers"
  if ! curl "${curl_options[@]}" -D "$headers_file" -o "$package_file" \
    "$base_url$package_path"; then
    echo "deploy_result=blocked"
    echo "reason=public_download_asset_unavailable"
    exit 1
  fi
  if ! tr -d '\r' <"$headers_file" | grep -Fqi \
    'cache-control: public, max-age=31536000, immutable'; then
    echo "deploy_result=blocked"
    echo "reason=public_download_cache_contract_mismatch"
    exit 1
  fi
  expected_sha="$(sha256sum "$public_download_source" | awk '{print $1}')"
  actual_sha="$(sha256sum "$package_file" | awk '{print $1}')"
  if [[ "$actual_sha" != "$expected_sha" ]]; then
    echo "deploy_result=blocked"
    echo "reason=public_download_sha_mismatch"
    exit 1
  fi
  echo "public_download_smoke_result=pass"
  echo "public_download_sha256=$actual_sha"
}

share_identity_hash_secret_file="${TWOBRAIN_SHARE_IDENTITY_HASH_SECRET_SECRET_FILE:-./secrets/graf_share_identity_hash_secret}"
ensure_generated_secret "$share_identity_hash_secret_file" 32
echo "share_identity_hash_secret_provision_result=pass"

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

verify_external_invitation_runtime() {
  if [[ "${TWOBRAIN_SHARE_EXTERNAL_INVITATIONS_ENABLED:-false}" != "true" ]]; then
    echo "external_invitation_config_result=disabled"
    return 0
  fi
  local receipt
  receipt="$("${compose[@]}" exec -T rec-api python -c '
from twobrain_rec_server.config import get_settings

settings = get_settings()
assert settings.share_external_invitations_enabled is True
assert settings.email_login_delivery_enabled is True
assert settings.postal_api_url is not None
assert settings.public_base_url is not None
assert settings.credential_encryption_key_file is not None
assert settings.share_identity_hash_secret_file is not None
assert len(settings.share_identity_hash_secret) >= 32
print("external_invitation_config_result=pass")
')"
  if ! grep -Fxq 'external_invitation_config_result=pass' <<<"$receipt"; then
    echo "deploy_result=blocked"
    echo "reason=external_invitation_config_invalid"
    exit 1
  fi
  local worker_receipt
  worker_receipt="$("${compose[@]}" exec -T rec-processing-worker python -c '
from twobrain_rec_server.config import get_settings

settings = get_settings()
assert settings.share_external_invitations_enabled is True
assert settings.email_login_delivery_enabled is True
assert settings.postal_api_url is not None
assert settings.public_base_url is not None
assert settings.credential_encryption_key_file is not None
assert settings.share_identity_hash_secret_file is not None
assert len(settings.share_identity_hash_secret) >= 32
print("external_invitation_worker_config_result=pass")
')"
  if ! grep -Fxq 'external_invitation_worker_config_result=pass' <<<"$worker_receipt"; then
    echo "deploy_result=blocked"
    echo "reason=external_invitation_worker_config_invalid"
    exit 1
  fi
  echo "external_invitation_config_result=pass"
  echo "external_invitation_worker_config_result=pass"
}

verify_processing_runtime_health() {
  local temporal_container processing_worker_container maintenance_container temporal_networks
  local temporal_restart_count processing_worker_restart_count maintenance_restart_count
  temporal_container="$("${compose[@]}" ps -q rec-temporal)"
  processing_worker_container="$("${compose[@]}" ps -q rec-processing-worker)"
  maintenance_container="$("${compose[@]}" ps -q rec-maintenance)"
  temporal_restart_count="$(docker inspect "$temporal_container" --format '{{.RestartCount}}' 2>/dev/null)" \
    || return 1
  processing_worker_restart_count="$(docker inspect "$processing_worker_container" --format '{{.RestartCount}}' 2>/dev/null)" \
    || return 1
  maintenance_restart_count="$(docker inspect "$maintenance_container" --format '{{.RestartCount}}' 2>/dev/null)" \
    || return 1
  [[ -n "$temporal_container" && -n "$processing_worker_container" && -n "$maintenance_container" ]] \
    && [[ "$(docker inspect "$temporal_container" --format '{{.State.Health.Status}}')" == "healthy" ]] \
    && [[ "$(docker inspect "$processing_worker_container" --format '{{.State.Health.Status}}')" == "healthy" ]] \
    && [[ "$(docker inspect "$maintenance_container" --format '{{.State.Status}}')" == "running" ]] \
    || return 1
  if [[ "$temporal_container" == "$temporal_container_baseline" ]]; then
    [[ "$temporal_restart_count" == "$temporal_restart_baseline" ]] || return 1
  else
    [[ "$temporal_restart_count" == "0" ]] || return 1
  fi
  if [[ "$processing_worker_container" == "$processing_worker_container_baseline" ]]; then
    [[ "$processing_worker_restart_count" == "$processing_worker_restart_baseline" ]] || return 1
  else
    [[ "$processing_worker_restart_count" == "0" ]] || return 1
  fi
  if [[ "$maintenance_container" == "$maintenance_container_baseline" ]]; then
    [[ "$maintenance_restart_count" == "$maintenance_restart_baseline" ]] || return 1
  else
    [[ "$maintenance_restart_count" == "0" ]] || return 1
  fi
  temporal_networks="$(docker inspect "$temporal_container" --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}')"
  [[ "$(sed '/^$/d' <<<"$temporal_networks" | wc -l | tr -d ' ')" == "2" ]] \
    && grep -Fxq 'twobrain-rec-private' <<<"$temporal_networks" \
    && grep -Fxq 'twobrain-rec-media-private' <<<"$temporal_networks"
}

capture_processing_runtime_baseline() {
  temporal_container_baseline="$("${compose[@]}" ps -q rec-temporal)"
  processing_worker_container_baseline="$("${compose[@]}" ps -q rec-processing-worker)"
  maintenance_container_baseline="$("${compose[@]}" ps -q rec-maintenance)"
  if [[ -n "$temporal_container_baseline" ]]; then
    temporal_restart_baseline="$(docker inspect "$temporal_container_baseline" --format '{{.RestartCount}}')"
  fi
  if [[ -n "$processing_worker_container_baseline" ]]; then
    processing_worker_restart_baseline="$(docker inspect "$processing_worker_container_baseline" --format '{{.RestartCount}}')"
  fi
  if [[ -n "$maintenance_container_baseline" ]]; then
    maintenance_restart_baseline="$(docker inspect "$maintenance_container_baseline" --format '{{.RestartCount}}')"
  fi
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
  export TWOBRAIN_LANGFUSE_RELEASE="$previous_sha"
  local available_services rollback_build_services rollback_up_services service
  available_services="$("${compose[@]}" config --services 2>/dev/null || true)"
  rollback_build_services=()
  rollback_up_services=()
  for service in rec-api rec-db-runtime-bootstrap rec-maintenance rec-reprocess-maintenance rec-prompt-optimization-worker rec-migrate rec-minio-init rec-processing-worker; do
    if grep -Fxq "$service" <<<"$available_services"; then
      rollback_build_services+=("$service")
    fi
  done
  for service in rec-api rec-migrate rec-minio rec-minio-init rec-temporal rec-processing-worker rec-maintenance; do
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
  --wait --wait-timeout 240 \
    rec-temporal rec-processing-worker rec-api rec-maintenance >/dev/null 2>&1 || rollback_failed=1
  verify_processing_runtime_health || rollback_failed=1
  verify_api_dispatch_gate false false || rollback_failed=1
  if [[ "$rollback_failed" == "0" ]]; then
    echo "rollback_result=pass"
    echo "rollback_target=compatibility_099"
    echo "rollback_runtime_sha=$expected_sha"
    echo "dispatch_stopped=true"
    echo "legacy_playback_guard_retained=true"
  else
    echo "rollback_attempt=compatibility_runtime_failed"
  fi
  return "$rollback_failed"
}

wait_for_previous_temporal_health() {
  local temporal_container="$1" attempt
  for ((attempt = 0; attempt < 60; attempt++)); do
    if docker exec "$temporal_container" temporal operator cluster health \
      --address rec-temporal:7233 >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

wait_for_previous_processing_pollers() {
  local temporal_container="$1" worker_hostname="$2" attempt workflow_pollers activity_pollers
  for ((attempt = 0; attempt < 60; attempt++)); do
    workflow_pollers="$(docker exec "$temporal_container" temporal task-queue describe \
      --address rec-temporal:7233 \
      --task-queue twobrain-rec-processing \
      --legacy-mode \
      --task-queue-type-legacy workflow 2>/dev/null)"
    activity_pollers="$(docker exec "$temporal_container" temporal task-queue describe \
      --address rec-temporal:7233 \
      --task-queue twobrain-rec-processing \
      --legacy-mode \
      --task-queue-type-legacy activity 2>/dev/null)"
    if { grep -Fq "@$worker_hostname" <<<"$workflow_pollers" \
        || grep -Fq "graf-processing:$worker_hostname" <<<"$workflow_pollers"; } \
      && { grep -Fq "@$worker_hostname" <<<"$activity_pollers" \
        || grep -Fq "graf-processing:$worker_hostname" <<<"$activity_pollers"; }; then
      return 0
    fi
    sleep 2
  done
  return 1
}

restore_previous_safe_processing_runtime() {
  local current_schema="$1"
  local rollback_failed=0 temporal_container processing_container worker_hostname media_container
  if [[ "$previous_schema_head" != "$expected_schema_head" \
    || "$current_schema" != "$previous_schema_head" ]]; then
    echo "rollback_result=blocked"
    echo "rollback_target=forward_fix_required"
    echo "rollback_backup_reference=${backup_reference:-unavailable}"
    return 1
  fi
  echo "rollback_fallback=previous_safe_processing_runtime"
  git reset --hard "$previous_sha" >/dev/null 2>&1 || rollback_failed=1
  export TWOBRAIN_LANGFUSE_RELEASE="$previous_sha"
  if [[ "$rollback_failed" == "0" ]]; then
    "${compose[@]}" build rec-api rec-processing-worker >/dev/null 2>&1 \
      || rollback_failed=1
  fi

  if [[ "$rollback_failed" == "0" ]]; then
    media_container="$("${compose[@]}" ps -aq rec-media-worker 2>/dev/null || true)"
    "${compose[@]}" stop rec-media-worker rec-api rec-processing-worker rec-maintenance rec-temporal \
      >/dev/null 2>&1 || true
    [[ -z "$media_container" ]] \
      || docker rm -f "$media_container" >/dev/null 2>&1 \
      || true
    "${compose[@]}" up -d --no-deps --no-build --force-recreate rec-temporal \
      >/dev/null 2>&1 || rollback_failed=1
  fi
  if [[ "$rollback_failed" == "0" ]]; then
    temporal_container="$("${compose[@]}" ps -q rec-temporal 2>/dev/null || true)"
    if [[ -z "$temporal_container" ]]; then
      rollback_failed=1
    else
      docker network disconnect twobrain-rec-media-private "$temporal_container" \
        >/dev/null 2>&1 || rollback_failed=1
      docker restart "$temporal_container" >/dev/null 2>&1 || rollback_failed=1
      wait_for_previous_temporal_health "$temporal_container" || rollback_failed=1
    fi
  fi

  if [[ "$rollback_failed" == "0" ]]; then
    "${compose[@]}" up -d --no-deps --no-build --force-recreate rec-processing-worker rec-maintenance \
      >/dev/null 2>&1 || rollback_failed=1
  fi
  if [[ "$rollback_failed" == "0" ]]; then
    processing_container="$("${compose[@]}" ps -q rec-processing-worker 2>/dev/null || true)"
    worker_hostname="$(docker inspect "$processing_container" --format '{{.Config.Hostname}}' \
      2>/dev/null || true)"
    if [[ -z "$processing_container" || -z "$worker_hostname" ]]; then
      rollback_failed=1
    else
      wait_for_previous_processing_pollers "$temporal_container" "$worker_hostname" \
        || rollback_failed=1
    fi
  fi

  if [[ "$rollback_failed" == "0" ]]; then
    TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=false \
      TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=false \
      "${compose[@]}" up -d --no-deps --no-build --force-recreate \
      --wait --wait-timeout 240 rec-api >/dev/null 2>&1 || rollback_failed=1
  fi
  if [[ "$rollback_failed" == "0" ]]; then
    verify_api_dispatch_gate false false || rollback_failed=1
    curl -fsS https://rec.2brain.pro/api/v1/health/live >/dev/null 2>&1 \
      || rollback_failed=1
    curl -fsS https://rec.2brain.pro/api/v1/health/ready >/dev/null 2>&1 \
      || rollback_failed=1
  fi

  if [[ "$rollback_failed" == "0" ]]; then
    echo "rollback_result=pass"
    echo "rollback_target=previous_safe_processing_runtime"
    echo "rollback_runtime_sha=$previous_sha"
    echo "dispatch_stopped=true"
    echo "media_worker_present=false"
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
  "${compose[@]}" stop rec-media-worker rec-maintenance rec-api >/dev/null 2>&1 || true
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
      if ! rollback_feature_database; then
        # Content lifecycle downgrades can intentionally refuse to remove
        # legacy lineage markers. Keep the expanded schema and run the
        # compatibility runtime instead of starting the old checkout against
        # an incompatible merge-head schema.
        echo "rollback_database_downgrade=blocked"
        if restore_compatibility_runtime; then
          return 0
        fi
        return 1
      fi
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
  if ! restore_compatibility_runtime; then
    if [[ "$previous_schema_head" == "$expected_schema_head" \
      && "$current_schema" == "$previous_schema_head" ]]; then
      restore_previous_safe_processing_runtime "$current_schema" || true
    else
      echo "rollback_result=blocked"
      echo "rollback_target=forward_fix_required"
      echo "rollback_backup_reference=${backup_reference:-unavailable}"
    fi
  fi
}

rollback_on_exit() {
  local status=$? public_download_restore_failed=0
  trap - EXIT INT TERM
  if [[ "$status" == "0" || "$deployment_complete" == "1" ]]; then
    return
  fi
  set +e
  echo "deploy_result=blocked"
  echo "reason=staged_rollout_failed"
  if [[ "$runtime_mutated" == "1" ]]; then
    "${compose[@]}" stop rec-api >/dev/null 2>&1 || true
  fi
  if ! restore_public_download; then
    echo "public_download_rollback_result=blocked"
    public_download_restore_failed=1
  elif [[ "$runtime_mutated" == "1" ]]; then
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
  if [[ "$public_download_restore_failed" == "1" ]]; then
    echo "rollback_result=blocked"
    echo "rollback_target=forward_fix_required"
    echo "rollback_backup_reference=${backup_reference:-unavailable}"
  fi
  cleanup_runtime_files || echo "runtime_cleanup_result=warning"
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

for runtime_service_secret in \
  "${GRAF_CREDENTIAL_ENCRYPTION_KEY_SECRET_FILE:-./secrets/graf_credential_encryption_key}" \
  "$share_identity_hash_secret_file" \
  "${TWOBRAIN_WEB_CSRF_SECRET_FILE:-./secrets/twobrain_web_csrf_secret}" \
  "${TWOBRAIN_POSTAL_API_SECRET_FILE:-./secrets/twobrain_postal_api_key}" \
  "${TWOBRAIN_YANDEX_CLIENT_SECRET_FILE:-./secrets/twobrain_yandex_client_secret}" \
  "${TWOBRAIN_VK_CLIENT_SECRET_FILE:-./secrets/twobrain_vk_client_secret}" \
  "${TWOBRAIN_SUPPORT_INCIDENT_GITHUB_TOKEN_FILE:-./secrets/twobrain_support_incident_github_token}" \
  "${TWOBRAIN_LANGFUSE_PUBLIC_KEY_SECRET_FILE:-./secrets/twobrain_langfuse_public_key}" \
  "${TWOBRAIN_LANGFUSE_SECRET_KEY_SECRET_FILE:-./secrets/twobrain_langfuse_secret_key}" \
  "${TWOBRAIN_MEDIASCRIBE_API_KEY_FILE:-./secrets/twobrain_mediascribe_api_key}" \
  "${TWOBRAIN_MINIO_API_ACCESS_KEY_FILE:-./secrets/twobrain_minio_api_access_key}" \
  "${TWOBRAIN_MINIO_API_SECRET_KEY_FILE:-./secrets/twobrain_minio_api_secret_key}" \
  "${TWOBRAIN_SMOKE_CREDENTIAL_FILE:-./secrets/twobrain_smoke_credential}" \
  "${TWOBRAIN_POSTGRES_PASSWORD_FILE:-./secrets/twobrain_postgres_password}" \
  "${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}" \
  "${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"; do
  if ! secure_runtime_secret_file "$runtime_service_secret"; then
    echo "deploy_result=blocked"
    echo "reason=runtime_service_secret_permissions_invalid"
    exit 1
  fi
done
echo "runtime_service_secret_permissions_result=pass"

if [[ "${TWOBRAIN_OUTCOME_GENERATION_ENABLED:-false}" == "true" \
  || "${TWOBRAIN_PROMPT_OPTIMIZATION_ENABLED:-false}" == "true" ]]; then
  litellm_secret_file="${TWOBRAIN_LITELLM_API_KEY_SECRET_FILE:-}"
  if [[ -z "$litellm_secret_file" ]] \
    || ! secure_runtime_secret_file "$litellm_secret_file"; then
    echo "deploy_result=blocked"
    echo "reason=litellm_secret_permissions_invalid"
    exit 1
  fi
  echo "litellm_secret_permissions_result=pass"
fi

if [[ "${TWOBRAIN_BILLING_PROVIDER_OBSERVATION_ENABLED:-false}" == "true" \
  || "${TWOBRAIN_BILLING_CHECKOUT_ENABLED:-false}" == "true" ]]; then
  if ! secure_runtime_secret_file "${TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE:-./secrets/twobrain_yookassa_secret}"; then
    echo "deploy_result=blocked"
    echo "reason=billing_secret_permissions_invalid"
    exit 1
  fi
fi

if [[ "${TWOBRAIN_BILLING_CHECKOUT_ENABLED:-false}" == "true" ]]; then
  for billing_secret in \
    "${TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE:-./secrets/twobrain_yookassa_webhook_secret}" \
    "${TWOBRAIN_BILLING_REFERRAL_SECRET_FILE:-./secrets/twobrain_billing_referral_secret}"; do
    if ! secure_runtime_secret_file "$billing_secret"; then
      echo "deploy_result=blocked"
      echo "reason=billing_secret_permissions_invalid"
      exit 1
    fi
  done
  echo "billing_secret_permissions_result=pass"
else
  echo "billing_secret_permissions_result=disabled"
fi

ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_APP_PASSWORD_FILE:-./secrets/twobrain_postgres_app_password}" 32
ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_MAINTENANCE_PASSWORD_FILE:-./secrets/twobrain_postgres_maintenance_password}" 32
ensure_generated_secret \
  "${TWOBRAIN_POSTGRES_MEDIA_PASSWORD_FILE:-./secrets/twobrain_postgres_media_password}" 32
echo "runtime_db_secret_provision_result=pass"
if ! secure_runtime_secret_file "${TWOBRAIN_POSTGRES_MAINTENANCE_PASSWORD_FILE:-./secrets/twobrain_postgres_maintenance_password}"; then
  echo "deploy_result=blocked"
  echo "reason=maintenance_database_secret_permissions_invalid"
  exit 1
fi
echo "maintenance_database_secret_permissions_result=pass"
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
disabled_billing_secret_count="$(grep -Fc "file: $disabled_billing_secret" /tmp/twobrain-rec-compose-deploy.yml || true)"
expected_disabled_billing_secret_count=3
if [[ "${TWOBRAIN_BILLING_CHECKOUT_ENABLED:-false}" == "true" ]]; then
  expected_disabled_billing_secret_count=0
elif [[ "${TWOBRAIN_BILLING_PROVIDER_OBSERVATION_ENABLED:-false}" == "true" ]]; then
  # Webhook and referral secrets remain intentionally disabled during GET/list-only observation.
  expected_disabled_billing_secret_count=2
fi
if [[ "$disabled_billing_secret_count" != "$expected_disabled_billing_secret_count" ]]; then
  echo "deploy_result=blocked"
  echo "reason=billing_enabled_compose_uses_disabled_secret_placeholder"
  exit 1
fi
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
  rec-prompt-optimization-worker \
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

capture_processing_runtime_baseline
runtime_mutated=1
"${compose[@]}" stop rec-api >/dev/null
sync_public_download
"${compose[@]}" stop rec-media-worker >/dev/null 2>&1 || true
TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED=false \
  TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED=false \
  "${compose[@]}" up -d --no-build --wait --wait-timeout 240 \
  rec-api \
  rec-migrate \
  rec-minio \
  rec-minio-init \
  rec-temporal \
  rec-processing-worker \
  rec-maintenance

if ! verify_processing_runtime_health; then
  echo "deploy_result=blocked"
  echo "reason=processing_runtime_readiness_failed"
  exit 1
fi
echo "temporal_readiness_result=pass"
echo "processing_worker_readiness_result=pass"

verify_external_invitation_runtime

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
verify_public_download

if ! verify_processing_runtime_health; then
  echo "deploy_result=blocked"
  echo "reason=final_processing_runtime_readiness_failed"
  exit 1
fi
echo "final_temporal_readiness_result=pass"
echo "final_processing_worker_readiness_result=pass"

echo "automatic_retry_result=required_post_deploy"
echo "backfill_inventory_result=required_post_deploy"
echo "range_playback_result=required_post_deploy"
echo "normalization_cleanup_result=required_post_deploy"

if [[ -n "$public_download_backup" ]] && ! rm -f -- "$public_download_backup"; then
  echo "public_download_cleanup_result=warning"
fi
if [[ -n "$public_download_temporary" ]] && ! rm -f -- "$public_download_temporary"; then
  echo "public_download_cleanup_result=warning"
fi
if ! cleanup_runtime_files; then
  echo "runtime_cleanup_result=warning"
fi
deployment_complete=1
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
