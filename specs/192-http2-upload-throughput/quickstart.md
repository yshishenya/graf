# Quickstart: Validate HTTP/2 upload throughput source-of-truth

## Prerequisites

- Run from the repository root.
- Do not print or persist webhook secret values.
- Production evidence below is from the completed hotfix; this repository slice does not require another production mutation.

## 1. Focused source check

```sh
test "$(grep -c '^[[:space:]]*http2_body_preread_size 2m;' infra/nginx/rec.2brain.pro.conf)" -eq 1
bash -n infra/scripts/install-billing-webhook-edge.sh
git diff --check
```

Expected: all commands exit 0.

## 2. Safe installer dry-run

When an operator has a valid local secret fixture, point the existing environment variable at it and run:

```sh
TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE=/operator/provided/path \
  infra/scripts/install-billing-webhook-edge.sh --dry-run
```

Expected: `billing_webhook_edge_result=dry_run`, `secret_validation=pass`, and planned checks include backup, install, Nginx test, reload, probes and automatic rollback. The secret value must not appear in output.

## 3. Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Expected: exit 0.

Validated on 2026-08-23: PASS — 1168 server tests passed; server lint,
Python compile and the overall fast lane completed with
`ci_local_result=pass mode=fast`.

## 4. Existing production evidence

- Before: 40.6 МБ in 97.6 s, approximately 3.33 Mbit/s.
- After synthetic HTTP/2: 34–38 Mbit/s.
- Real GRAF/WKWebView request `a69e664c-73f5-4bf5-ae1f-61f4637f1820`: `202 Accepted` in 8.219 s.
- Pure transfer: 7.68 s, 42.29 Mbit/s.
- MinIO, DB and finalization: about 540 ms.
- Nginx syntax, reload, health and readiness: passed; reload did not restart the master process.
- Rollback backup: `/etc/nginx/sites-available/rec.2brain.pro.conf.before-http2-upload-window-20260823T021938Z`.

## Rollback

For a later deployment failure, use the existing installer's automatic rollback. For the current live hotfix, restore the recorded backup only if a regression is observed and re-run Nginx syntax, reload, health/readiness and upload probes.
