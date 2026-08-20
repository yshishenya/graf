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
| Route ownership и useful error documents | `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetWorkspaceTests\|DesktopCabinetConfigurationTests'` | 74 passed |
| GET-only headers и route allowlist | `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetNavigationRequestPolicyTests\|DesktopCabinetRoutePolicyTests'` | 25 passed |
| Web/embedded account form endpoints | `PYTHONPATH=apps/server/src uv run --project apps/server pytest -q apps/server/tests/contract/test_account_routes.py` | 26 passed, 2 existing dependency warnings |
| Финальные email-link HTML/CSS контракты | focused account/static-asset selection | 7 passed, 2 existing dependency warnings |
| CSRF retry после invalid/expired кода | focused PostgreSQL integration selection | 2 passed, следующая попытка остаётся 400, не 403 |
| Repository fast gate | `infra/scripts/ci-local.sh --fast` | 1103 passed, lint passed, compile passed; 2 existing dependency warnings |
| Whitespace | `git diff --check` | passed |

## Metadata-safe app smoke

- Локально подписанная и установленная `GRAF Dev` открыла полностью видимый
  экран кода после единственного POST start; общего экрана ошибки встреч не было.
- Неверный код и rate-limit ранее оставались локальными понятными документами.
- Успешный синтетический код сразу вернул видимую страницу аккаунта с сообщением
  о подключении; пустого окна, access-denied и ручного reload не было.
- Metadata-only server trace подтвердил один POST start, отсутствие GET/405 на
  start endpoint, один POST verify с 303 и один конечный GET account с 200.
- Значения синтетического email и кода в evidence не сохранены.

## Independent reviews

- Correctness review: no findings after the active/pending-route guard was
  narrowed to the matching URL.
- Auth/security and embedded UX review: no findings.
- GitHub review found and closed one CSRF retry gap in displayed email-link
  errors; a focused integration regression now submits the returned token and
  proves the next attempt remains an auth error rather than a CSRF 403.
- Ponytail review first removed two duplicated test fragments (about 20 lines);
  the final reviewed diff is lean with no further findings.

## Remaining release evidence

- Signed/notarized GRAF hotfix build and metadata-safe production smoke.
