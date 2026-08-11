# Deployment evidence: Feature 140 closeout

Дата: 2026-08-11 (Europe/Moscow)

Это metadata-only evidence. Секреты, provider IDs, customer data, payloads,
аудио и транскрипты намеренно не сохраняются.

| Поле | Значение |
|---|---|
| Production host | `2brain.dev:/opt/projects/2brain-rec` |
| Branch | `master` |
| Deployed SHA | `b19dd0fe1920147598164839d82f93deb1b0c2ac` |
| Migration head | `0067_referral_bound_attributed` |
| Checkout | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` |
| Deploy result | `pass` |
| Backup/restore rehearsal | `pass` |
| Production smoke/cleanup | `pass`, residue empty (post-deploy run) |
| Live/ready probes | HTTP 200; YooKassa production webhook без секрета HTTP 401 |
| Live RLS metadata probe | `pass`, 104/104 верификатора; 105/105 прикладных таблиц enabled+forced |

Операция не является YooKassa canary и не доказывает доставку provider webhook:
production edge CIDR allowlist, TLS/header injection, test/real-shop canary и
independent security/finance/legal/QA sign-offs остаются launch gates T078/T080.
