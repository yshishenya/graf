# Проверка

## Среда
Рабочая ветка, серверное uv-окружение, Node и Swift. Только синтетические встречи. Использовать существующий calendar/cabinet UI harness, не открывать личные встречи для evidence.

## Сценарии
1. Python unit tests для user_time/view_models, PostgreSQL integration для meeting list; Z/offset, оба направления сортировки, ручная загрузка/NULL и поиск по полной локальной дате.
2. Node/браузер: смешать local/server rows при всех доступных sort/filter; повторить update; дата и порядок остаются, локальная строка не дублирует server после завершения upload.
3. Прогнать UTC, Asia/Yekaterinburg, America/New_York, Asia/Kathmandu; полночь, смену года, DST 23/25h; invalid zone и cookies disabled без reload loop.
4. Список → detail → shared → calendar → account → billing/admin: ДД.ММ.ГГГГ, ЧЧ:ММ, deadline содержит пояс. HTMX даёт тот же результат.
5. Swift focused checks: восстановленная запись, стабильный id, локальная дата и VoiceOver, сроки хранения. Счётчики длительности не изменились.
6. `git diff --check`, Ruff; scoped CI fallback когда PR не создан. Полный CI/подпись/релиз не заявляются.

7. Параллельные запросы с разными поясами, исключение/reset, отсутствие контекста вне запроса. GET вне allowlist и POST не повторяются; cookie disabled не вызывает повторов.

## Evidence
Результаты ниже относятся к локальной рабочей копии F252, не к production.

## Перед реализацией

Analyze: после согласования FR-001 и FR-011 нет CRITICAL/HIGH findings. FR-001–011 и SC-001–004 покрыты T001–T005; 100% требований имеют task. Reviewer checklist: ux 6/6, time-contract 6/6 (отдельный reviewer). Issue canon validation PASS; tasks T001–T005 → #6664–#6668.

T001 baseline: `cd apps/server && uv run --frozen --extra dev pytest tests/unit/test_user_time.py -q` → 9 passed. `TZ=Asia/Yekaterinburg node apps/server/tests/browser/user-time.test.cjs` → passed (формат, duration, blocked cookie, запрет reload без разрешения, защита от цикла). Это focused evidence, не CI/release proof.


## Итоговая проверка реализации

- Общий Python context/formatter: 11 проверок, включая UTC, offsets/naive, DST, параллельные запросы, reset после ошибки, запрет POST и только проверенные GET платежей.
- Базовый focused набор времени/аккаунта/admin/rendering: 30 passed.
- Список: 187 unit, 30 PostgreSQL integration; связанные detail/calendar/shared: 13 passed. После согласования accepted+immutable ревизий смешанная хронология проверена повторно: 1 passed.
- Shared/invitation: 18 PostgreSQL tests (known/manual/unknown, preview и public links), отдельный invitation contract: 1 passed; unit+contracts: 196 passed.
- Account lifecycle, admin audit и public-share: 32 passed. Admin browser contract: 6 passed на PostgreSQL. Billing/account/share/static contracts без БД: 193 passed; 6 ошибочных setup без БД разрешены указанным отдельным PostgreSQL-прогоном.
- `TZ=Asia/Yekaterinburg node apps/server/tests/browser/user-time.test.cjs`: PASS. Проверены UTC, Екатеринбург, Катманду, Нью-Йорк/DST, date-only, naive/fractional ISO, blocked cookies и reload guard.
- Реальный Chromium `mixed-meeting-list.test.cjs`: PASS, все 7 сортировок, поиск, фильтры, стабильные ID, upload handoff, HTMX. Дополнительно подтверждён единый UTC для native generated title и даты при blocked cookies.
- Финальные focused Swift: 76 passed, включая generated title prefix в мосте, пользовательские заголовки, восстановленное начало, duration, календарь и сроки хранения.
- Живой UI локального синтетического стенда: один момент показан как 06.09.2026, 02:30 в списке и карточке; позиции плеера 00:00/00:40 не смещены. В аккаунте видны Asia/Yekaterinburg и объяснение автоматического пояса. Переход к /settings на harness не реализован (405); прямой /settings/account проверен. Установленный GRAF и ручной VoiceOver не проверялись с этой сборкой.
- В живом Krisp изучены список, сортировка и карточка; наблюдения записаны без частного содержимого в research.md.

## Convergence

Проверены FR-001–011, SC-001–004, 12 acceptance scenarios, решения plan и ограничения constitution: хранение/расчёты, capture/consent, tenant/access, deletion, evidence и публичная дистрибуция. Buildable gaps: 0; дополнительных задач реализации нет. Учтены обнаруженные при review blocked cookies, первая ссылка на платёж, generated title и неизвестные даты shared. Требования и реализация сходятся; это не подтверждение PR/release gates.

## Границы evidence

Risk lane: significant feature / high-risk UX. GitHub governance-fast требует согласованного implementation commit и точного PR SHA. Полный CI, release-full, production smoke, сборка/подпись/нотаризация и обновление установленного приложения не выполнялись. Issues остаются открытыми до PR/release evidence; отметки в tasks означают реализацию, а не опубликованный релиз.


## Заключительный fast-прогон

`GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast` → **PASS**, 597 секунд. Финальная рабочая копия: 807 Swift tests, 1408 server unit tests, 93 изменённых contract/integration tests — все прошли. Также PASS: process preflight, Spec Kit governance, governance tests, portable harness, macOS build/ContractValidation, server Ruff/compile, shell syntax, CI contracts, compose config, evidence scan, whitespace и documentation consistency.

Первоначальные расхождения в пяти старых проверках (московское время/секунды, сокращённый месяц, смещение записи в календарном блоке) заменены точными ожиданиями общего формата; заключительный прогон прошёл целиком. Код продукта после последних исправлений не менялся во время этого прогона.

Это диагностический запуск по незакоммиченной рабочей копии: receipt имеет `status=ambiguous`, `next_gate=full_before_release`, поэтому не разрешает merge или release. Базовый HEAD: `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`; изменения F252 ещё не имеют собственного SHA. Канонический GitHub `governance-fast` на точном SHA остаётся следующей проверкой после разрешённого коммита/PR.

## Дополнение T006–T009
Проверить один select без режимов: автозаполнение Екатеринбург, поиск Москва/Kathmandu/UTC+05:45, предпросмотр; сохранение New York меняет дату на предыдущий день в list/detail/search; Cancel не меняет аккаунт. Повторный вход и другое устройство сохраняют выбор; anonymous использует устройство. Проверить неверный IANA с одновременной сменой theme (ни одно поле не сохраняется), no-JS, ошибку сети с повтором. Миграция: default Moscow → NULL, выбранные Moscow/UTC сохранены, новый аккаунт NULL; rollback запрещает потерю новых поясов. Native: trusted metadata, logout/session switch, stale callback, in-process offline, cold-start device fallback. Проверить текущие и зимние/летние offsets, полчаса и четверть часа.

### Evidence дополнения: 2026-09-06
- T006: 17 PostgreSQL integration tests, включая upgrade/downgrade, реальные auth sessions, web/desktop, приоритет настройки и атомарное отклонение: `/tmp/graf252-timezone-integration.log`. Дополнительная проверка неуспешного audit события включена в итоговый fast.
- Поиск/хронология и migration chain: 46 PostgreSQL tests PASS, `/tmp/graf252-timezone-query.log`; сохранённый New York меняет SQL-поиск с 01.01.2027 на 31.12.2026 вопреки cookie Екатеринбурга.
- T007: `TZ=Asia/Yekaterinburg node tests/browser/user-time.test.cjs`, `NODE_PATH=/Users/yshishenya/.npm/_npx/e41f203b7505f1fb/node_modules node tests/browser/timezone-settings.test.cjs`, аналогично mixed-meeting-list.test.cjs. Агент audit_web_dates проверил Chromium+локальный HTTP: поиск, preview, reset, network/422 retry, CSRF/FormData/303 и no-JS. Путь NODE_PATH следует взять из доступной установки Playwright, он не является зависимостью продукта.
- T008: 124 Swift tests PASS (`/tmp/graf-native-context-final.log`), реальная сборка TwoBrainRecApp (`/tmp/graf-native-context-build.log`) и ContractValidation (`/tmp/graf-native-context-contract.log`). Настоящий WKWebView: main document против iframe, изоляция origin/user/session, auth reset до completion и stale callback; custody использует выбранный пояс.
- Родительский browser QA: production templates/assets на synthetic localhost:8872; найдено Москва, выбрано Europe/Moscow, POST→303→`/settings/account?preferences=saved`. Никаких реальных аккаунтов/встреч.
- Полный запуск `pytest tests/unit` без PostgreSQL непригоден для 64 DB-зависимых тестов; 1336 прошли, один прежний default Moscow expectation обновлён к NULL. Итоговый fast запускает необходимую PostgreSQL среду.
- Requirements reviewer: timezone-setting.md 5/5 PASS, CRITICAL 0/HIGH 0; LOW D001–D004 устранены. Issue sync T006–T009: #6702–#6705, прежняя umbrella #6663.

### Финальный диагностический gate дополнения
`GRAF_CI_ALLOW_DIRTY=1 infra/scripts/ci-local.sh --fast` — PASS, 615 секунд, `/tmp/graf252-timezone-fast.log`: 813 Swift, 1411 server unit, 126 changed server contract/integration, 224 governance, 66 CI contracts. Пройдены сборка, ContractValidation, Ruff, compile, compose, evidence scan, whitespace/docs. Receipt `.dev/ci-evidence/ci-fast-6ff8db3ee18d-b037654c5750.json` остаётся `ambiguous/partial`, `full_before_release`: дерево содержит незафиксированные изменения. Этот запуск подтверждает локальную диагностику, не PR/release gate.
В финальной browser проверке выбранная Moscow сохранилась после reload; список показал 06.09.2026, 00:30 вместо 02:30. При viewport390 ширина документа390, горизонтального переполнения нет. Все418 IANA-значений каталога распознаны текущими Intl и Foundation. Скриншоты содержат только synthetic harness и лежат в ignored `.playwright-cli/`.
