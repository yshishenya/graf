# Deployment evidence: Feature 140 closeout

Дата: 2026-08-11 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `8e29ff3b361a0518ac09605e3d0027aa2e16571f` |
| Migration head | `0066_referral_attributed_rls` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass` |
| Production smoke/cleanup | `pass`, residue empty (post-deploy run) |
| Live/ready probes | HTTP 200; YooKassa production webhook без секрета HTTP 401 |
| Live RLS metadata probe | `pass`, 104/104 верификатора; 105/105 прикладных таблиц enabled+forced |

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist, TLS/header injection, test/real-shop canary и
independent security/finance/legal/QA sign-offs остаются launch gates T078/T080.
