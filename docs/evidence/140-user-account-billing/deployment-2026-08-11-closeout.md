# Deployment evidence: Feature 140 closeout

Дата: 2026-08-12 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `a0ed01ee442dba2e4bfc2908326f8dda875d0ef4` (`v2026.08.12.1`) |
| Migration head | `0071_fair_use_capability_prefix` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass`, `/opt/projects/2brain-rec/backups/20260812T034850Z` |
| Production smoke/cleanup | `pass`, 39 database rows and 3 object keys removed, residue empty |
| Live/ready probes | HTTP 200; dedicated `:8443` untrusted probe 403; direct backend no-secret 401 |
| Live RLS metadata probe | `pass`, 106/106 прикладных таблиц enabled+forced |
| Webhook edge | `pass`: `nginx -t`, TLS 1.2/1.3, YooKassa CIDR allowlist, 256 KiB, rate limit, secret overwrite; backup `/etc/nginx/backups/graf-billing-webhook-20260812T035449Z` |

Окно edge-обслуживания: `2026-08-12 05:54 CEST` (`03:54 UTC`), reload
завершился с кодом `0`; повторный privileged `nginx -t` в `06:51 CEST` —
успешен. Backup содержит pre-edge `site.conf`; installer автоматически
восстанавливает его и reload-ит Nginx при ошибке syntax/reload/post-reload
probe. Checkout во время и после окна оставался выключен.

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist/TLS/header injection подтверждены. Controlled
provider delivery, test/real-shop canary и independent security/finance/legal/QA
sign-offs остаются launch gate T078. Технический security/redaction review T080
закрыт отдельным standard scan и focused/live metadata-only evidence.
