# Deployment evidence: Feature 140 closeout

Дата: 2026-08-11 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `83c46fcf8cf8283b40080994cec3b9969e1a7da6` |
| Migration head | `0069_fair_use_review_constraints` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass` |
| Production smoke/cleanup | `pass`, residue empty (post-deploy run) |
| Live/ready probes | HTTP 200; YooKassa production webhook без секрета HTTP 401 |
| Live RLS metadata probe | `pass`, 106/106 прикладных таблиц enabled+forced |

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist, TLS/header injection, test/real-shop canary и
independent security/finance/legal/QA sign-offs остаются launch gates T078/T080.
