#!/usr/bin/env bash
set -euo pipefail
mode="${1:---dry-run}"
[[ "$mode" == --dry-run || "$mode" == --execute ]] || { echo 'usage: install-summary-share-edge.sh --dry-run|--execute' >&2; exit 2; }
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
site_source="$repo_root/infra/nginx/rec.2brain.pro.conf"
limit_source="$repo_root/infra/nginx/graf-summary-share-limit.conf"
site_target=/etc/nginx/sites-available/rec.2brain.pro.conf
limit_target=/etc/nginx/conf.d/graf-summary-share-limit.conf
[[ -f "$site_source" && -f "$limit_source" ]] || { echo 'summary_share_edge=missing_config' >&2; exit 1; }
if [[ "$mode" == --dry-run ]]; then
  echo 'summary_share_edge=dry_run'
  echo 'checks=backup,compare_existing_site,install,nginx_test,reload,headers,health,rollback_on_failure'
  exit 0
fi
[[ "$(id -u)" == 0 ]] || { echo 'summary_share_edge=root_required' >&2; exit 1; }
umask 077
backup_dir="$(mktemp -d /etc/nginx/graf-summary-backup.XXXXXX)"
cp -a "$site_target" "$backup_dir/site.conf"
[[ ! -e "$limit_target" ]] || cp -a "$limit_target" "$backup_dir/limit.conf"
# Refuse to overwrite unrelated live edits. Only the two owned locations differ.
python3 - "$site_target" "$site_source" <<'PY'
import re,sys
from pathlib import Path
live=Path(sys.argv[1]).read_text();target=Path(sys.argv[2]).read_text()
if live.strip()==target.strip():
 sys.exit(0)
target=re.sub(r'    location ~ \^/\(api/v1/cabinet/\(public-shares.*?\n    }\n\n','',target,flags=re.S)
if live.strip()!=target.strip():
 raise SystemExit('summary_share_edge=live_site_drift; inspect before installation')
PY
rollback() {
  cp -a "$backup_dir/site.conf" "$site_target"
  if [[ -f "$backup_dir/limit.conf" ]]; then cp -a "$backup_dir/limit.conf" "$limit_target"; else rm -f "$limit_target"; fi
  nginx -t >/dev/null 2>&1 && systemctl reload nginx >/dev/null 2>&1 || true
}
trap 'rollback' ERR
install -m 0644 "$limit_source" "$limit_target"
install -m 0644 "$site_source" "$site_target"
nginx -t
systemctl reload nginx
python3 - <<'PY'
import urllib.request,urllib.error
url='https://rec.2brain.pro/api/v1/cabinet/public-shares/synthetic-invalid-edge-check?workspace_id=00000000-0000-0000-0000-000000000000'
try: response=urllib.request.urlopen(url,timeout=15)
except urllib.error.HTTPError as error: response=error
assert response.status in (404,429,503), 'unexpected public probe state'
for key,value in [('Cache-Control','no-store'),('Referrer-Policy','no-referrer'),('X-Robots-Tag','noindex')]:
 assert value in response.headers.get(key,''), 'missing protected error header'
assert urllib.request.urlopen('https://rec.2brain.pro/api/v1/health/live',timeout=15).status==200
print('summary_share_edge=pass; invalid_token_headers=pass; health=pass')
PY
trap - ERR
