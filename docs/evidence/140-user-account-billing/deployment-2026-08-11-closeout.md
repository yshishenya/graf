# Deployment evidence: Feature 140 closeout

Дата: 2026-08-13 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `32ce03c2334bc842cbb9871f966432ecf0ac33ca` |
| Migration head | `0071_fair_use_capability_prefix` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass`, `/opt/projects/2brain-rec/backups/20260813T111644Z` |
| Production smoke/cleanup | `pass`, 39 database rows and 3 object keys removed, residue empty |
| Live/ready probes | HTTP 200; dedicated `:8443` untrusted probe 403; direct backend no-secret 401 |
| Live RLS metadata probe | `pass`, 106/106 прикладных таблиц enabled+forced |
| Webhook edge | `pass`: `nginx -t`, TLS 1.2/1.3, YooKassa CIDR allowlist, 256 KiB, rate limit, secret overwrite; backup `/etc/nginx/backups/graf-billing-webhook-20260812T035449Z` |

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist/TLS/header injection подтверждены. Controlled
provider delivery, test/real-shop canary и independent security/finance/legal/QA
sign-offs остаются launch gates T078/T080.
