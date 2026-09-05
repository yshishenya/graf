# F242 — результаты проверки 2026-09-06

## Версия и границы доказательства

Ветка: `codex/242-cabinet-audit-fixes`. Базовый source SHA: `41bf51c7da86212503d971bce09e44640c087f4e`.
Проверялась изменённая рабочая копия, не базовый commit и не общий dev server.
SHA256 tracked code/test diff: `a2407935f52d7eaf06cb57ecfc7f8591ab9f7b477e4b7880a4a5bdec739ce092`.
SHA256 нового test_cabinet_audit_fixes.py: `8d1847ec5d935b6cd9dba34944bb22f88f6e789c8972eca1b0f3aced519ba690`.
Это evidence рабочей копии, не exact-SHA evidence будущего PR. После validation пользователь явно разрешил коммит и push: «коммита и push ревью». Публикация и GitHub gate выполняются следующим шагом.

## Проверки

- Baseline до реализации: 258 passed. Новые регрессии воспроизвели прежние дефекты; недостаток synthetic fixture исправлен до повторного прогона.
- Полная команда quickstart: **305 passed, 2 warnings, 3.97 s**. Включает billing UI/accessibility/security/RLS, settings, navigation, shell, JS runtime contracts, recording accessibility, trial и 29 новых случаев.
- Повтор перед коммитом: **305 passed, 2 warnings, 4.59 s**; хеши кода/нового теста совпали с указанными выше. Ruff, whitespace, Spec Kit governance/frozen doctor и changelog validator повторно PASS. Повторное correctness/Ponytail review: замечаний нет, лишних зависимостей и абстракций нет.
- Два предупреждения прежние: pytest assert rewrite для postgres fixture и deprecated Pydantic Field extra. Общая БД не подключалась.
- `ruff check` на всех изменённых Python файлах: PASS.
- `git diff --check`: PASS.
- `scripts/check_spec_kit_governance.py`: PASS, включая frozen bootstrap doctor.
- `scripts/validate-changelog-fragments.py`: PASS.
- Mandatory issue-canon ensure/validate: PASS, последний validator проверил 300 открытых Spec Kit issues. Собственный umbrella bootstrap metadata исправлен, чужие issues не изменялись.
- Независимые requirements checklists: 7/7. Повторная проверка кода и sibling microdiff: замечаний нет. Ponytail: PASS, native details, existing helper/handler/model, без новых зависимостей/миграций.

## Browser QA

Browser plugin skill отсутствует; использован установленный Playwright CLI, отдельный Chromium session и временный синтетический сервер. Реальные templates/static assets взяты из этой рабочей копии; server/снимки/скрипты вне git.

| Проверка | Результат |
|---|---|
| Page identity / meaningful content / error overlay | PASS: billing overview, plans, history, synthetic meeting |
| Console health | 0 ошибок, 0 предупреждений на проверенных страницах |
| Wide 1440×1000 / narrow 390×844 с JS | PASS для изменённых billing элементов; documentWidth=390, без горизонтального overflow |
| Theme: menu → Вид → Светлая → POST → новая страница | PASS: отправлено только theme=light; реальный preferences handler сохранил en-US/UTC; следующая страница light |
| Trial overview/plans disclosure | PASS: условия, отдельная финальная кнопка, preview dates; сворачивание Enter без POST |
| Trial без JS, 1440×1000 | PASS: focus summary → Enter → финальная кнопка доступна |
| History help с/без contact, пустая история | PASS: anchor #billing-help получает фокус; email/mailto/copy либо честный unavailable + возврат |
| Pending transcript | PASS: короткая строка и hook; общий recovery UI и live regions сохранены |

Synthetic meeting server не предоставляет processing API: общий recovery показывает ожидаемое сообщение о невозможности обновить статус. Это проверка сохранения восстановления при сбое, не доказательство реальной обработки записи. Нормальные/terminal/no-speech/preserved ветви дополнительно покрыты существующими тестами.

## Ограничения и handoff

- Без JS на 390px обнаружено прежнее ограничение общего shell: широкие billing cards обрезаются. CSS этой фичей не менялся; наблюдение передано соседней задаче F244, не объявлено исправленным. Native confirmation как механизм работает без JS, responsive no-JS всего кабинета не сертифицирован.
- Native WK navigation/preferences route отдельно F243; серверный embedded handler проверен, установленное macOS приложение не пересобиралось.
- Нет реальных trial/payment/deletion, provider вызовов, приватных данных или снимков в git.
- Lane: high-risk-product. Локальный fast не запускался: он diagnostic/offline fallback; authoritative PR gate — GitHub governance-fast после commit/PR. Full CI, release/deploy, dry-run не запускались — release не запрошен.
- Converge по текущим FR-001–007 и US1–US4: новых обязательных правок кода не найдено. SC-003/T006 (PR и exact-SHA gate) остаются открытым handoff, а не выполненным результатом.

## Публикация и обратная связь CI

- Создан PR #6582: https://github.com/yshishenya/graf/pull/6582. Первый commit/push: `8762e1ecceca8455a9b29be12c46ff08d4a790e3`.
- Первый `governance-fast` https://github.com/yshishenya/graf/actions/runs/33995530838 завершился **FAIL**: Ruff I001 в трёх test-файлах. До этого прошли 224 governance, 1391 server unit и 80 changed contract tests. Этот run не является успешным PR gate.
- Причина расхождения локальной проверки: глобальный Ruff 0.2.1 вместо закреплённого project Ruff 0.15.20. Исправлены только группы импортов; в quickstart добавлена команда с frozen project environment. Код приложения после первого коммита не менялся.
- Повтор в frozen окружении (Python 3.14.6): `ruff check .` всего сервера PASS; те же 305 проверок PASS, 2 warnings, 4.01 s. Предупреждения этого окружения: pytest fixture rewrite и Starlette/httpx deprecation; ошибок нет.
- Связи T001–T006 дополнены каноническим `(Issue #...)` для машинной проверки закрытия задач. T006 остаётся открыт до успешного нового exact-SHA gate.
- Автоматическое code review Codex ограничено квотой, CodeRabbit пропустил автоматическое ревью. Они не засчитываются как положительное ревью; локальная и независимая проверки описаны выше. Внешний security review проверяется отдельно.
