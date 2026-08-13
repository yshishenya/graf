#!/usr/bin/env bash
set -euo pipefail

mode="${1:---dry-run}"
case "$mode" in
  --dry-run|--execute) ;;
  *) echo "usage: $0 [--dry-run|--execute]" >&2; exit 2 ;;
esac

cd "$(dirname "$0")/../.."
repo_root="$(pwd -P)"
site_source="$repo_root/infra/nginx/rec.2brain.pro.conf"
limit_source="$repo_root/infra/nginx/graf-billing-webhook-limit.conf"
secret_source="${TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE:-$repo_root/secrets/twobrain_yookassa_webhook_secret}"
site_target="/etc/nginx/sites-available/rec.2brain.pro.conf"
limit_target="/etc/nginx/conf.d/graf-billing-webhook-limit.conf"
secret_target="/etc/nginx/snippets/graf-billing-webhook-secret.conf"

[[ -f "$site_source" && -f "$limit_source" ]] || {
  echo "billing_webhook_edge_result=blocked"
  echo "reason=repository_config_missing"
  exit 1
}
[[ -f "$secret_source" && ! -L "$secret_source" ]] || {
  echo "billing_webhook_edge_result=blocked"
  echo "reason=webhook_secret_missing"
  exit 1
}
webhook_secret="$(tr -d '\r\n' < "$secret_source")"
[[ "$webhook_secret" =~ ^[A-Za-z0-9_-]{32,128}$ ]] || {
  echo "billing_webhook_edge_result=blocked"
  echo "reason=webhook_secret_format"
  exit 1
}

if [[ "$mode" == "--dry-run" ]]; then
  cat <<EOF
billing_webhook_edge_result=dry_run
site_target=$site_target
limit_target=$limit_target
secret_target=$secret_target
secret_validation=pass
planned_checks=backup,install,nginx_test,reload,negative_probe,health,automatic_rollback
EOF
  exit 0
fi

[[ "$(id -u)" == "0" ]] || {
  echo "billing_webhook_edge_result=blocked"
  echo "reason=root_required"
  exit 1
}

umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/etc/nginx/backups/graf-billing-webhook-$stamp"
stage_dir="$(mktemp -d /tmp/graf-billing-webhook-edge.XXXXXX)"
cleanup() { rm -rf -- "$stage_dir"; }
trap cleanup EXIT

mkdir -p "$backup_dir" /etc/nginx/snippets
cp -a -- "$site_target" "$backup_dir/site.conf"
[[ ! -e "$limit_target" ]] || cp -a -- "$limit_target" "$backup_dir/limit.conf"
[[ ! -e "$secret_target" ]] || cp -a -- "$secret_target" "$backup_dir/secret.conf"

install -m 0644 -- "$site_source" "$stage_dir/site.conf"
install -m 0644 -- "$limit_source" "$stage_dir/limit.conf"
{
  printf 'proxy_set_header X-Billing-Webhook-Secret "'
  printf '%s' "$webhook_secret"
  printf '";\n'
} > "$stage_dir/secret.conf"
chmod 0600 "$stage_dir/secret.conf"

rollback() {
  cp -a -- "$backup_dir/site.conf" "$site_target"
  if [[ -e "$backup_dir/limit.conf" ]]; then
    cp -a -- "$backup_dir/limit.conf" "$limit_target"
  else
    rm -f -- "$limit_target"
  fi
  if [[ -e "$backup_dir/secret.conf" ]]; then
    cp -a -- "$backup_dir/secret.conf" "$secret_target"
  else
    rm -f -- "$secret_target"
  fi
  nginx -t >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true
}

install -m 0644 -- "$stage_dir/site.conf" "$site_target"
install -m 0644 -- "$stage_dir/limit.conf" "$limit_target"
install -m 0600 -- "$stage_dir/secret.conf" "$secret_target"

if ! nginx -t; then
  rollback
  echo "billing_webhook_edge_result=blocked"
  echo "reason=nginx_test"
  echo "rollback=attempted"
  exit 1
fi
if ! systemctl reload nginx; then
  rollback
  echo "billing_webhook_edge_result=blocked"
  echo "reason=nginx_reload"
  echo "rollback=attempted"
  exit 1
fi

health_status="$(curl -fsS -o /dev/null -w '%{http_code}' https://rec.2brain.pro/api/v1/health/live || true)"
direct_status="$(curl -sS -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' -d '{}' \
  http://127.0.0.1:18081/api/v1/billing/providers/yookassa/webhook/production || true)"
edge_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' -d '{}' \
  https://rec.2brain.pro:8443/api/v1/billing/providers/yookassa/webhook/production || true)"
test_edge_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' -d '{}' \
  https://rec.2brain.pro:8443/api/v1/billing/providers/yookassa/webhook/test || true)"
if [[ "$health_status" != "200" || "$direct_status" != "401" || "$edge_status" != "403" || "$test_edge_status" != "403" ]]; then
  rollback
  echo "billing_webhook_edge_result=blocked"
  echo "reason=post_reload_probe"
  echo "health_status=$health_status"
  echo "direct_backend_status=$direct_status"
  echo "untrusted_edge_status=$edge_status"
  echo "untrusted_test_edge_status=$test_edge_status"
  echo "rollback=attempted"
  exit 1
fi

echo "billing_webhook_edge_result=pass"
echo "backup_reference=$backup_dir"
echo "secret_validation=pass"
echo "health_status=$health_status"
echo "direct_backend_status=$direct_status"
echo "untrusted_edge_status=$edge_status"
echo "untrusted_test_edge_status=$test_edge_status"
