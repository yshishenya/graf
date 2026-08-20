# Evidence: Стабильное подключение email в приложении

**Date**: 2026-08-20

Все результаты metadata-only. Реальные email, коды, cookies, tokens, nonces,
account identifiers и private meeting content не использовались и не записаны.

## Test-first proof

- До production fix focused Swift build завершился ожидаемой ошибкой: regression
  test потребовал отсутствующий request-aware route predicate.
- После fix тот же focused selection прошёл: 74 tests, 0 failures.

## Focused validation

| Контракт | Команда | Результат |
|---|---|---|
| Route ownership и useful error documents | Отдельные запуски `DesktopCabinetWorkspaceTests` и `DesktopCabinetConfigurationTests` | 74 passed |
| GET-only headers и route allowlist | Отдельные запуски `DesktopCabinetNavigationRequestPolicyTests` и `DesktopCabinetRoutePolicyTests` | 25 passed |
| Web/embedded account form endpoints | `PYTHONPATH=apps/server/src uv run --project apps/server pytest -q apps/server/tests/contract/test_account_routes.py` | 26 passed, 2 existing dependency warnings |
| Финальные email-link HTML/CSS контракты | `test_cabinet_static_assets_contract.py` | 51 passed, 2 existing dependency warnings |
| CSRF retry после invalid/expired кода | focused PostgreSQL integration selection | 2 passed, следующая попытка остаётся 400, не 403 |
| Repository fast gate | `infra/scripts/ci-local.sh --fast` | 1103 passed, lint passed, compile passed; 2 existing dependency warnings |
| Whitespace | `git diff --check` | passed |

## Metadata-safe app smoke

- Локально подписанная и установленная `GRAF Dev` открыла полностью видимый
  экран кода после единственного POST start; общего экрана ошибки встреч не было.
- Неверный код и rate-limit ранее оставались локальными понятными документами.
- Финальная установленная сборка повторно прошла invalid-code → retry → resend:
  ошибка осталась внутри формы, повтор не стал CSRF 403, новый код успешно
  завершил подключение.
- Успешный синтетический код сразу вернул видимую страницу аккаунта с сообщением
  о подключении; пустого окна, access-denied и ручного reload не было.
- Metadata-only server trace подтвердил один POST start, отсутствие GET/405 на
  start endpoint, один POST verify с 303 и один конечный GET account с 200.
- Значения синтетического email и кода в evidence не сохранены.

## Independent reviews

- Независимый correctness review финального рабочего дерева: APPROVED.
- Auth/security review проверил все 9 изменённых runtime/test файлов. Найденный
  fail-closed gap для HTML 401 и workspace recovery воспроизведён двумя
  regression assertions и исправлен в общем response policy; выживших security
  findings после проверки attack path нет.
- GitHub review found and closed one CSRF retry gap in displayed email-link
  errors; a focused integration regression now submits the returned token and
  proves the next attempt remains an auth error rather than a CSRF 403.
- Ponytail review first removed two duplicated test fragments (about 20 lines);
  the final reviewed diff is lean with no further findings.

## Release closeout

- Implementation PR #5456 and release PR #5457 were merged without unresolved
  review threads. Release SHA `6651db70` is tagged `v2026.08.20.2`.
- The exact-SHA release gate passed: 697 macOS tests; 3066 server tests with one
  expected skip; 47 strict PostgreSQL/RLS checks with one expected skip; lint,
  compile and release checks passed.
- Guarded production deploy passed after backup and restore rehearsal. Runtime,
  API, Temporal and workers report the release SHA and healthy readiness;
  production smoke and cleanup passed without rollback.
- The public universal macOS app and package use Developer ID Application and
  Installer. Apple notarization, stapling, Gatekeeper and Developer ID to
  Developer ID continuity all passed.
- The public Sparkle feed, archive and package were downloaded again and their
  signatures, lengths and SHA-256 values matched the reviewed artifacts.
- Installed production GRAF completed a real Sparkle update from `2026.08.19.2`
  to `2026.08.20.2`, relaunched into the production meeting list with the
  existing session, and opened the account settings with email already shown as
  confirmed. No macOS permission prompt or generic meeting-load error appeared.
- Aggregate-only post-deploy audit found zero HTTP 500, HTTP 405, traceback and
  automatic email-link GET replay matches.
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.20.2
- Detailed metadata-only receipt:
  `docs/deployments/2brain-rec/release-v2026.08.20.2.md`.
