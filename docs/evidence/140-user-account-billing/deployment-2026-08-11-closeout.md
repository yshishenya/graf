# Deployment evidence: Feature 140 closeout

Дата: 2026-08-12 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `ec114a81dc92e7e29d59f91c3111bdf7acb32070` |
| Migration head | `0071_fair_use_capability_prefix` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass`, `/opt/projects/2brain-rec/backups/20260811T221934Z` |
| Production smoke/cleanup | `pass`, 39 database rows and 3 object keys removed, residue empty |
| Live/ready probes | HTTP 200; YooKassa production webhook без секрета HTTP 401 |
| Live RLS metadata probe | `pass`, 106/106 прикладных таблиц enabled+forced |

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist, TLS/header injection, test/real-shop canary и
independent security/finance/legal/QA sign-offs остаются launch gates T078/T080.
