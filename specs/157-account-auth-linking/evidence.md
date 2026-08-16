# Evidence: linked auth methods

Проверки выполнены на disposable PostgreSQL; production identities, tokens and
meeting content не использовались.

| Проверка | Результат |
| --- | --- |
| `tests/integration/test_account_merge.py` | 4 passed |
| `test_app_role_gets_only_proof_bound_account_merge_access` | 1 passed; web role не получил общий maintenance-доступ |
| Auth contract + web owner session integration | 83 passed после исправления совместимого API-ответа |
| Account/merge contract + provider-link unit | 32 passed |
| `infra/scripts/ci-local.sh --fast` | pass; 1093 unit tests, lint, compile |
| `infra/scripts/ci-local.sh --full` | pass; macOS 685 tests, server 3013 passed / 1 skipped, strict RLS 41 passed / 1 skipped, compose and deployment evidence scan passed |
| Security diff scan | 0 reportable findings; 23/23 changed-file review rows closed |
| Ruff + Python compileall | pass |

Покрыты metadata-only preview, сохранение meeting/workspace IDs, пустой
duplicate auto-link, email-session → OAuth auto-link, cancel, expiry, replay,
ambiguous-email recovery, CSRF и browser/desktop route parity.

Не является release evidence: production smoke и deploy не входят в эту рабочую
итерацию до отдельного release gate. Production-safe boundary теперь закрыта:
`twobrain_rec_app` получает только контекст конкретного proof-bound merge intent,
а общий maintenance context остаётся доступен только
`twobrain_rec_maintenance`.
