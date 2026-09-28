# Tasks: F279 — подключение и повторяющиеся встречи

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/calendar.md, quickstart.md.
**Lane**: high-risk. Custom checklists UX 8/8, security 8/8 PASS (review-report.md).
**Tests**: обязательны по spec и выбранному процессу; синтетические данные, без частных ссылок.

## Phase 1: Setup

- [ ] T001 Подготовить синтетические сценарии J01–J07/S01–S10 и проверки регрессий в apps/server/tests/contract/test_calendar_join_series_contract.py и apps/server/tests/unit/test_calendar_series.py; подтвердить исходные сбои перед реализацией.

## Phase 2: Foundation

- [X] T002 Добавить общий разрешённый запрос события и версионированную identity (workspace, owner, source, external_calendar, provider_series) в apps/server/src/twobrain_rec_server/calendar/series.py и api/calendar.py; исключать отменённые/удалённые/отключённые/невыбранные данные; сохранить старые ключи и отдельные snapshots. Покрывает FR-005–008, FR-012, FR-015–018.

## Phase 3: US1 — подключиться к выбранной встрече

Цель: GRAF сохраняет экран и передаёт ровно одну актуальную ссылку системному обработчику.
Независимая проверка: J01–J07, SC-001/002; отсутствие auth во внешнем запросе, stale-session отказ, двойное нажатие, query/password сохранён.

- [X] T003 [US1] Реализовать JSON join-target с no-store и общим resolver для browser open в apps/server/src/twobrain_rec_server/api/calendar.py, api/schemas.py; контрактные тесты доступа и отмены. FR-001,005,006,018.
- [X] T004 [US1] Реализовать узкий UUID-мост и единый opener в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetCalendarJoinBridge.swift, Calendar/CalendarMeetingOpener.swift, Upload/DesktopUploadClient.swift и местах вызова; состояния около кнопки, один запрос, отмена при смене сессии/документа, проверенные native-механизмы и HTTPS fallback; Swift tests. FR-001–007,020.

## Phase 4: US2 — одна карточка серии

Цель: текущий/ближайший экземпляр и явный признак повторения даже при одном событии.
Независимая проверка: 12 экземпляров → одна карточка, независимые серии не объединяются, частая серия не вытесняет соседние; S01–S04,S06,S09.

- [X] T005 [US2] Добавить проекцию overview и группировку до LIMIT с owner/privacy фильтрами в apps/server/src/twobrain_rec_server/calendar/series.py, api/calendar.py, cabinet/queries.py, cabinet/view_models.py; current starts_at <= now < ends_at, latest current then UUID, иначе earliest future then UUID. Сохранить occurrence API и напоминания. FR-008–013,016–018.
- [ ] T006 [US2] Реализовать карточку серии и раскрытие дат в apps/server/src/twobrain_rec_server/cabinet/rendering.py и cabinet/static/cabinet/; явная выбранная дата, скрытие title/time во всех атрибутах, keyboard/VoiceOver, темы и узкое окно; browser tests. FR-009–013,016,019; SC-003,006,007.

## Phase 5: US3 — даты и отдельные записи

Цель: переносы/отмены не смешивают записи; история отражает только доступные данные.
Независимая проверка: S05,S07,S08,S10; чужие записи не раскрываются в ссылках/счётчиках.

- [X] T007 [US3] Добавить ограниченную историю и доступные записи в apps/server/src/twobrain_rec_server/calendar/series.py, api/calendar.py и cabinet/queries.py: range <=366 суток, default now-180..now+30, limit 1..50 default20, signed cursor <=2048 ASCII/TTL1h с owner/workspace/series/range, 422 на неверный ввод; 0..N записей только по надёжной связи, без новой области доступа и расширения retention. Подключить пагинацию к панели и тестировать разрыв доступа/коллизии/переносы. FR-008,010–018; SC-004,005.

## Phase 6: Validation

- [ ] T008 Выполнить converge и проверки из specs/279-calendar-join-series/quickstart.md, добавить changes/unreleased/F279.yaml и обновить validation.md; независимое ревью происхождения/доступа, server+Swift+browser suite, затем GRAF Dev через dev-harness после согласованного commit. Зафиксировать реально проверенную совместимость приложений; exact-SHA CI/merge/release отдельно, не закрывать issues без evidence. FR-001–020, SC-001–007.

## Dependencies and execution

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008. Сначала unit/contract тесты каждой части, затем код. US1 можно проверить до UI серии; US2 — без записей US3; US3 использует готовую identity US2.

## Parallel examples

US1: чтение официальных механизмов открытия и подготовка синтетической матрицы независимы от запуска server tests. US2: unit группировки и browser сценарии можно запускать одновременно после кода. US3: проверки SQL доступа и cursor не изменяют одни файлы. Изменения общих файлов выполняются последовательно.

## Strategy

Сначала исправить подключение, затем карточку серии, затем историю/записи. Не считать локальную реализацию выпущенной. Commit — только после проверки и явного разрешения пользователя; production не входит в текущий этап.

## Tracker

tasks.md остаётся источником реализации. Все задачи имеют открытого внешнего владельца:

- T001, T002: https://github.com/yshishenya/graf/issues/7359
- T003, T004: https://github.com/yshishenya/graf/issues/7360
- T005, T006, T007: https://github.com/yshishenya/graf/issues/7361
- T008: https://github.com/yshishenya/graf/issues/7362

## Команды проверки и окружение

macOS, Python 3.13.3; apps/server/.venv создан через uv sync --frozen --extra dev. Server: из apps/server `uv run --frozen pytest tests/unit/test_calendar_series.py tests/contract/test_calendar_join_series_contract.py -q`; затем календарные unit/contract/integration suites. PostgreSQL использует существующий disposable fixture. Swift: `swift test --package-path apps/macos --filter 'CalendarMeetingOpenerTests|EmbeddedCabinetCalendarJoinBridgeTests|DesktopUploadClientTests|DesktopCabinetSessionBridgeTests'` без parallel. Browser: node apps/server/tests/browser/calendar_series.mjs; native UI — только штатный dev-harness/GRAF Dev после validation и согласованного commit.

## Phase 7: Convergence

- [X] T009 Устранить оставшийся устаревший запуск из меню macOS и напоминания: получать join-target по UUID непосредственно при нажатии, проверять сессию после ответа и исключить параллельный повтор; добавить Swift-регрессии. FR-001,004,006; plan: единый opener (partial, HIGH). Владелец: https://github.com/yshishenya/graf/issues/7360.

## Состояние проверки реализации

T002–T005, T007 и T009 подтверждены исходниками, независимым ревью и автоматическими наборами (validation.md). Их GitHub issues остаются открытыми до совокупной приёмки и слитого PR. T001 остаётся открытой для завершения всей матрицы J/S и доказательств, T006 — для VoiceOver/тем в GRAF Dev, T008 — для локального установленного приложения и последующих gates. Это не утверждение готовности релиза.

Повторный analyze после T009: задача связана с FR-001/004/006 и существующим #7360; новых противоречий/непокрытых обязательных требований нет. Converge повторно проверил новый resolver для всех изменённых точек входа; оставшиеся пункты — приёмка, не недостающие участки реализации.
