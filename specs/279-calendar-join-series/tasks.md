# Tasks: F279 — подключение и повторяющиеся встречи

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/calendar.md, quickstart.md.
**Lane**: high-risk. Custom checklists UX 8/8, security 8/8 PASS (review-report.md).
**Tests**: обязательны по spec и выбранному процессу; синтетические данные, без частных ссылок.

## Phase 1: Setup

- [X] T001 (Issue #7359) Подготовить синтетические сценарии J01–J07/S01–S10 и проверки регрессий в apps/server/tests/contract/test_calendar_join_series_contract.py и apps/server/tests/unit/test_calendar_series.py; подтвердить исходные сбои перед реализацией.

## Phase 2: Foundation

- [X] T002 (Issue #7359) Добавить общий разрешённый запрос события и версионированную identity (workspace, owner, source, external_calendar, provider_series) в apps/server/src/twobrain_rec_server/calendar/series.py и api/calendar.py; исключать отменённые/удалённые/отключённые/невыбранные данные; сохранить старые ключи и отдельные snapshots. Покрывает FR-005–008, FR-012, FR-015–018.

## Phase 3: US1 — подключиться к выбранной встрече

Цель: GRAF сохраняет экран и передаёт ровно одну актуальную ссылку системному обработчику.
Независимая проверка: J01–J07, SC-001/002; отсутствие auth во внешнем запросе, stale-session отказ, двойное нажатие, query/password сохранён.

- [X] T003 (Issue #7360) [US1] Реализовать JSON join-target с no-store и общим resolver для browser open в apps/server/src/twobrain_rec_server/api/calendar.py, api/schemas.py; контрактные тесты доступа и отмены. FR-001,005,006,018.
- [X] T004 (Issue #7360) [US1] Реализовать узкий UUID-мост и единый opener в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetCalendarJoinBridge.swift, Calendar/CalendarMeetingOpener.swift, Upload/DesktopUploadClient.swift и местах вызова; состояния около кнопки, один запрос, отмена при смене сессии/документа, проверенные native-механизмы и HTTPS fallback; Swift tests. FR-001–007,020.

## Phase 4: US2 — одна карточка серии

Цель: текущий/ближайший экземпляр и явный признак повторения даже при одном событии.
Независимая проверка: 12 экземпляров → одна карточка, независимые серии не объединяются, частая серия не вытесняет соседние; S01–S04,S06,S09.

- [X] T005 (Issue #7361) [US2] Добавить проекцию overview и группировку до LIMIT с owner/privacy фильтрами в apps/server/src/twobrain_rec_server/calendar/series.py, api/calendar.py, cabinet/queries.py, cabinet/view_models.py; current starts_at <= now < ends_at, latest current then UUID, иначе earliest future then UUID. Сохранить occurrence API и напоминания. FR-008–013,016–018.
- [X] T006 (Issue #7361) [US2] Реализовать карточку серии и раскрытие дат в apps/server/src/twobrain_rec_server/cabinet/rendering.py и cabinet/static/cabinet/; явная выбранная дата, скрытие title/time во всех атрибутах, keyboard/VoiceOver, темы и узкое окно; browser tests. FR-009–013,016,019; SC-003,006,007.

## Phase 5: US3 — даты и отдельные записи

Цель: переносы/отмены не смешивают записи; история отражает только доступные данные.
Независимая проверка: S05,S07,S08,S10; чужие записи не раскрываются в ссылках/счётчиках.

- [X] T007 (Issue #7361) [US3] Добавить ограниченную историю и доступные записи в apps/server/src/twobrain_rec_server/calendar/series.py, api/calendar.py и cabinet/queries.py: range <=366 суток, default now-180..now+30, limit 1..50 default20, signed cursor <=2048 ASCII/TTL1h с owner/workspace/series/range, 422 на неверный ввод; 0..N записей только по надёжной связи, без новой области доступа и расширения retention. Подключить пагинацию к панели и тестировать разрыв доступа/коллизии/переносы. FR-008,010–018; SC-004,005.

## Phase 6: Validation

- [X] T008 (Issue #7362) Выполнить converge и проверки из specs/279-calendar-join-series/quickstart.md, добавить changes/unreleased/F279.yaml и обновить validation.md; независимое ревью происхождения/доступа, server+Swift+browser suite, затем GRAF Dev через dev-harness после согласованного commit. Зафиксировать реально проверенную совместимость приложений; exact-SHA CI/merge/release отдельно, не закрывать issues без evidence. FR-001–020, SC-001–007.

## Dependencies and execution

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008. Сначала unit/contract тесты каждой части, затем код. US1 можно проверить до UI серии; US2 — без записей US3; US3 использует готовую identity US2.

## Parallel examples

US1: чтение официальных механизмов открытия и подготовка синтетической матрицы независимы от запуска server tests. US2: unit группировки и browser сценарии можно запускать одновременно после кода. US3: проверки SQL доступа и cursor не изменяют одни файлы. Изменения общих файлов выполняются последовательно.

## Strategy

Сначала исправить подключение, затем карточку серии, затем историю/записи. Не считать локальную реализацию выпущенной. Commit — только после проверки и явного разрешения пользователя; production не входит в текущий этап.

## Tracker

tasks.md остаётся источником реализации. Все задачи связаны с внешним владельцем; актуальное состояние находится в GitHub:

- T001, T002: https://github.com/yshishenya/graf/issues/7359
- T003, T004: https://github.com/yshishenya/graf/issues/7360
- T005, T006, T007: https://github.com/yshishenya/graf/issues/7361
- T008: https://github.com/yshishenya/graf/issues/7362

## Команды проверки и окружение

macOS, Python 3.13.3; apps/server/.venv создан через uv sync --frozen --extra dev. Server: из apps/server `uv run --frozen pytest tests/unit/test_calendar_series.py tests/contract/test_calendar_join_series_contract.py -q`; затем календарные unit/contract/integration suites. PostgreSQL использует существующий disposable fixture. Swift: `swift test --package-path apps/macos --filter 'CalendarMeetingOpenerTests|EmbeddedCabinetCalendarJoinBridgeTests|DesktopUploadClientTests|DesktopCabinetSessionBridgeTests'` без parallel. Browser: node apps/server/tests/browser/calendar_series.mjs; native UI — только штатный dev-harness/GRAF Dev после validation и согласованного commit.

## Phase 7: Convergence

- [X] T009 (Issue #7360) Устранить оставшийся устаревший запуск из меню macOS и напоминания: получать join-target по UUID непосредственно при нажатии, проверять сессию после ответа и исключить параллельный повтор; добавить Swift-регрессии. FR-001,004,006; plan: единый opener (partial, HIGH). Владелец: https://github.com/yshishenya/graf/issues/7360.

## Состояние проверки реализации

T002–T005, T007 и T009 подтверждены исходниками, независимым ревью и автоматическими наборами (validation.md). Их GitHub issues остаются открытыми до совокупной приёмки и слитого PR. T001/T006/T010 подтверждены завершающей матрицей и тестами; VoiceOver отдельно принят пользователем. T008 подтверждена повторным GRAF Dev на обновлённой базе; окончательные GitHub checks проверяются отдельно на PR SHA. Это не утверждение готовности релиза.

Повторный analyze после T009: задача связана с FR-001/004/006 и существующим #7360; новых противоречий/непокрытых обязательных требований нет. Converge повторно проверил новый resolver для всех изменённых точек входа; оставшиеся пункты — приёмка, не недостающие участки реализации.

## Phase 8: Convergence — завершение приёмки

- [X] T010 (Issue #7362) Завершить доказательства S07/C02/SC-007: API-регрессия отзыва доступа и удаления записи внутри доступной серии; неизменность активной записи при успешном/ошибочном/устаревшем Join; воспроизводимый замер trusted click и раскрытия серии в локальном production browser harness. Пути: apps/server/tests/contract/test_calendar_join_series_contract.py, apps/macos/Shared/Tests/CalendarMeetingOpenerTests.swift, apps/server/tests/browser/calendar_series.mjs. FR-014/020, SC-005/007 (partial evidence). Владелец: https://github.com/yshishenya/graf/issues/7362.


Все T001–T010 выполнены локально. Повторный build/promote/live smoke и UI выполнены на `547315475621e365a29e269e67331346a47a248c`. Последующий документационный commit не меняет продуктовый код. До merge issues остаются открытыми; release-full выполняется один раз на замороженном post-merge кандидате.


Повторный converge по четырём замечаниям PR #7363 уточнил существующие T003/T004/T005/T008/T009: граница истории, нестандартный HTTPS-порт, явное восстановление через браузер и ожидание результата напоминанием. Объём исходных FR-003/006/007/010 не расширен; новые feature/task IDs не создаются. Повторный analyze: контракт, quickstart J08–J10/S11 и регрессии согласованы; окончательные CI/Dev требуют нового SHA. Локальные доказательства — validation.md.

Второй повторный converge/analyze после PR-ревью уточнил те же T003/T004/T005/T008/T009: готовность документа, ошибка меню, issued window курсора и ожидание напоминания. FR-004/006/007/010/016 покрыты quickstart J11–J13/S12 и новыми регрессиями. Исходный объём не расширен, новых задач/дублей issues нет; текущий SHA требует повторного CI и установленного Dev.

Третий повторный converge/analyze по PR уточнил существующие T003/T004/T005/T008/T009: eligibility истории, актуальность prompt во время resolver и локальная ошибка браузерного Join. J14/J15/S13 покрывают FR-003/004/007/010; задачи и границы фичи сохранены.

Четвёртый повторный converge/analyze уточнил T003/T004/T007/T008/T009: сохранение Join при штатном обновлении DOM, соответствие host-политик и подтверждение browser-сессии перед handoff. J16/J17 покрывают FR-003/004/006/007 и SC-002; endpoint POST — подтверждение существующего read-only resolver, новых продуктовых задач не добавлено.

Финальное уточнение четвёртой группы: J18 закрывает смену сессии после авторизации задержанного POST через несекретное поколение cookie. Проверены все централизованные issuer/clear пути и неизменность обычного renewal; дополнительные auth/CSRF regression входят в существующие T003/T008 и SC-002. Общая модель авторизации и bearer cookie не меняется.


Пятый повторный converge/analyze уточнил T003/T004/T007/T008/T009: нормализация доменов при выборе приложения, свежий resolver отдельной карточки уведомления и ограниченная выборка записей. J19/J20/S14 соответствуют FR-002/004/005/007/013/014/017. Контракт API, план и модель данных согласованы; новых номеров/дублей задач нет. Все календарные точки запуска повторно проверены независимым reviewer.


Шестой повторный converge/analyze: J21/S15 закрывают межповерхностное дублирование Join и самостоятельное использование history cursor через полночь. FR-004/006/010/016 и прежние T003/T004/T007/T008/T009; спецификация, план и контракт согласованы, новых задач не требуется.

## Сверка выпуска 2026-09-30

PR #7363 слит как `04768db6d3bac13ea3121b1171f605aa32062c14`.
F279 включена в опубликованный [v2026.09.29.1](https://github.com/yshishenya/graf/releases/tag/v2026.09.29.1),
SHA `8da0e2b635f7628a0ad22a5739bd5c47d1784c76`.
[release-full](https://github.com/yshishenya/graf/actions/runs/36626949196)
прошёл на этом SHA; authoritative artifact подтверждает одинаковый SHA сервера
и macOS, `status=passed`, `authoritative_full=true`, `skipped_gates=[]`.

Выше сохранены исторические результаты этапов до слияния; они не описывают
текущее состояние выпуска. Связи `(Issue #N)` в строках T001–T010 позволяют
проверить владельцев существующим `validate-issue-closeout.py`. Закрытие задач
выполняется после живой проверки PR и результатов CI, общая задача — последней.
Это только исправление документации: новый выпуск и повторный `release-full`
не требуются. Ограничения проверки Teams и отдельной карточки уведомления
сохранены в [итоговых результатах PR](https://github.com/yshishenya/graf/pull/7363#issuecomment-5877116913);
VoiceOver подтверждён пользователем и повторно не проверяется.
