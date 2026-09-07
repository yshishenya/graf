# Tasks: системная консоль GRAF — Feature 254

**Ветка:** `codex/254-system-admin-console`. **Источник требований:** [spec.md](spec.md), [план](plan.md), [контракты](contracts/api.md), [приёмка](acceptance.md). Реализация начата. Состояние и проверки первого участка — [implementation-evidence.md](implementation-evidence.md). T000 — общая GitHub задача, не implementation checkbox.

Перед кодом прочитать все reviewer-owned checklist. При открытых пунктах следовать gate проекта; исполнитель не меняет их состояние. Предлагаемые новые пути ниже создаются при реализации, existing modules переиспользуются. Номера миграций назначаются по актуальным Alembic heads.


## Основание

- [X] T001 Зафиксировать ревью требований и матрицу реализации. Пути: `specs/254-system-admin-console/checklists/`; `specs/254-system-admin-console/acceptance.md`.
  - Результат: Прочитать reviewer-owned gates; не отмечать их исполнителем. Сохранить решения ревью и связность контрактов, затем обновить базовый SHA перед кодом.
  - Зависимости: нет. Приёмка: AC-001, AC-003, AC-019, AC-033, AC-038, AC-041.
  - Подготовительная проверка выполнена; это не прохождение перечисленных runtime AC. Внешнее закрытие #6712 ожидает PR и его проверки.

- [X] T002 Создать системную схему и ограниченные права PostgreSQL. Пути: `apps/server/src/twobrain_rec_server/db/models/system_admin.py`; `apps/server/src/twobrain_rec_server/db/tenant_context.py`; `apps/server/src/twobrain_rec_server/db/session.py`; `apps/server/src/twobrain_rec_server/db/migrations/versions/`; `apps/server/scripts/bootstrap_runtime_database_roles.py`.
  - Результат: System_control, restrictive RLS поверх PUBLIC policies, genuine session_user, no BYPASSRLS/role inheritance; узкие SELECT/command policies, повторный bootstrap и pool reset; системные секреты недоступны app/maintenance.
  - Зависимости: T001. Приёмка: AC-001, AC-003, AC-036, AC-041.
  - Основание выполнено: миграции 0086–0087, отдельные личности/сессии, фиксированные разрешения, scoped grants и case context, restrictive RLS всех доступных сейчас отношений, отдельный pool и повторный bootstrap. Расширение проекций и прав предметных таблиц остаётся в T008–T035; это не прохождение всех AC фичи. Внешнее закрытие #6713 ожидает PR и проверки точного SHA.

- [ ] T003 Добавить долговечные команды и неизменяемый аудит. Пути: `apps/server/src/twobrain_rec_server/system_admin/operations.py`; `apps/server/src/twobrain_rec_server/system_admin/audit.py`; `apps/server/src/twobrain_rec_server/system_admin/schemas.py`.
  - Результат: Preview 5min, expected versions, idempotency, outbox/dispatcher через существующий Temporal, узкие claim/continue/result worker helpers, per-target durable continuation/fence, target scope, revoke до effect-start, continuation после sent, отдельный actual system actor.
  - Зависимости: T002. Приёмка: AC-004, AC-012, AC-024, AC-033, AC-036, AC-037.
  - В работе: реализован неизменяемый runtime-аудит разрешённых и запрещённых чтений, фактический actor/session/purpose/target/reason, отдельная транзакция до выдачи полномочия; сбой аудита закрывает доступ. Добавлены preview/commit/worker claim/continuation для двух команд встречи и проверки повторов/отзыва/версии. Maintenance dispatcher двух команд подключён к существующим Temporal/удалению; добавлены атомарная domain reference и HTTP/формы. Остальные handlers, batch и scheduled approvals ещё предстоят.

- [ ] T004 Изолировать процесс консоли и выключенный по умолчанию запуск. Пути: `apps/server/src/twobrain_rec_server/system_admin/app.py`; `infra/`; `apps/server/src/twobrain_rec_server/db/rls_validation.py`.
  - Результат: Отдельный service из того же образа, отдельный origin/host-only cookie/CORS/CSRF и route proxy, отдельный credential/pool; обычный server/worker не получает system credential. Read/command admission flags и безопасный rollback.
  - Зависимости: T002. Приёмка: AC-001, AC-035, AC-041, AC-042.
  - В работе: отдельный ASGI процесс, Origin/CSRF/cookies, optional Compose overlay и nginx template. Полное подключение инфраструктурной проверки и rollback ещё не завершено.

## US1

- [ ] T005 [US1] Реализовать отдельный вход, второй фактор и восстановление. Пути: `apps/server/src/twobrain_rec_server/system_admin/auth.py`; `apps/server/src/twobrain_rec_server/system_admin/web.py`; `apps/server/scripts/manage_system_admin.py`.
  - Результат: Пароль/scrypt, TOTP RFC vectors, recovery, CSRF, TTL/rate limits, version-bound challenges, recovery только enrolment, key rotation, reset без снятия MFA, bootstrap/recovery без публичного bypass.
  - Зависимости: T002,T003,T004. Приёмка: AC-001, AC-002, AC-003, AC-004.
  - В работе: проверены scrypt/TOTP, version-bound challenges, enrolment/recovery/reset, HTTP login и операторский init/recover; реализация всех оставшихся auth/rotation/delivery сценариев продолжается.

- [ ] T006 [US1] Реализовать назначения ролей и отзыв действующего доступа. Пути: `apps/server/src/twobrain_rec_server/system_admin/permissions.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/admins.html`.
  - Результат: Фиксированная role matrix, temporary object grants, бессрочный последний superadmin под lock, auth_version, no self elevation, revoke streams и delayed commands.
  - Зависимости: T005. Приёмка: AC-001, AC-002, AC-003, AC-004, AC-007.
  - В работе: HTTP и формы приглашений, повторной отправки, ролей и временных прав; сохранённые состояния отправки и отзыв старых ссылок. Проверены last-admin race, границы grants и MFA. Отзыв будущих потоков аудио и всех типов команд остаётся в зависимых задачах.

- [ ] T007 [US1] Доказать изоляцию входа и PostgreSQL на конкурентных запросах. Пути: `apps/server/tests/integration/test_system_admin_security.py`; `apps/server/tests/contract/test_system_admin_auth.py`.
  - Результат: Реальные роли PostgreSQL; подмена GUC/SET ROLE/cookie; product-origin attack, fake request/worker GUC, challenge reset/revoke race, recovery-only APIs, replay, same TOTP race, two last-admin removals, bootstrap reset, session pool leakage и audit outage.
  - Зависимости: T006. Приёмка: AC-001, AC-002, AC-003, AC-004, AC-036, AC-041.

## US2

- [ ] T008 [US2] Собрать оболочку консоли, глобальный поиск и таблицу пользователей. Пути: `apps/server/src/twobrain_rec_server/system_admin/web.py`; `apps/server/src/twobrain_rec_server/system_admin/queries.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/`.
  - Результат: 16 разделов, SQL cursor/filter/sort, POST private search, source/time/stale/no data, per-field permission, labels русские и сохранение формы при conflict.
  - Зависимости: T007. Приёмка: AC-005, AC-006, AC-008, AC-038, AC-039, AC-042.

- [ ] T009 [US2] Добавить карточки пространств, аккаунтов и управление сессиями. Пути: `apps/server/src/twobrain_rec_server/system_admin/queries.py`; `apps/server/src/twobrain_rec_server/auth/account_closure.py`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: Личный payer отдельно от corporate membership; блокировка продукта/системы раздельно, no force merge, batch session revoke<=100, защита организации.
  - Зависимости: T008. Приёмка: AC-006, AC-007, AC-034, AC-037, AC-040.

## US3

- [ ] T010 [US3] Добавить глобальную карточку встречи и разделение метаданных/контента. Пути: `apps/server/src/twobrain_rec_server/system_admin/queries.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/meeting.html`.
  - Результат: Версии/стадии/source/time, no-speech, полный текст с частичной загрузкой/поиском/таймкодами; несуществующие исторические версии не выдумывать.
  - Зависимости: T008. Приёмка: AC-008, AC-009, AC-010, AC-011, AC-013, AC-039.
  - В работе: отдельный доступ к заголовку/расшифровке, выбор существующего опубликованного результата общим helper, 100 фрагментов на страницу, поиск через POST, привязка страниц к версии и очистка при отзыве. Добавлены карточка метаданных, постраничные версии/попытки и состояния удаления. Добавлен канонический аудиоплеер и скачивание с отдельным доступом; итоги и retained-диагностика ещё не завершены.

- [ ] T011 [US3] Защитить аудио, экспорт и сохранённую диагностику системным доступом. Пути: `apps/server/src/twobrain_rec_server/cabinet/egress.py`; `apps/server/src/twobrain_rec_server/system_admin/web.py`; `apps/server/src/twobrain_rec_server/system_admin/audit.py`.
  - Результат: Явный system egress вместо admin shortcut; stream ticket и Range recheck; revision integrity; distinct retained view; content download/export права, no signed public URL.
  - Зависимости: T010. Приёмка: AC-004, AC-009, AC-010, AC-013, AC-036, AC-039.

- [ ] T012 [US3] Проверить просмотр всех пространств, отзыв и целостность выгрузок. Пути: `apps/server/tests/integration/test_system_admin_content.py`.
  - Результат: Фактический system actor, запрет metadata role через скрытые поля, malicious transcript, content audit до байтов и после удаления.
  - Зависимости: T011. Приёмка: AC-004, AC-008, AC-009, AC-010, AC-013, AC-039.

## US4

- [ ] T013 [US4] Подключить повтор обработки к существующему ядру. Пути: `apps/server/src/twobrain_rec_server/api/processing.py`; `apps/server/src/twobrain_rec_server/processing/store.py`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: Вынести существующий dispatch в общий service без дубля; commit до Temporal, old published result, dedup quota, ambiguous attempt без blind resubmit.
  - Зависимости: T003,T012. Приёмка: AC-012, AC-013, AC-033.

- [ ] T014 [US4] Подключить удаление встречи и закрытие аккаунта с точным отчётом. Пути: `apps/server/src/twobrain_rec_server/deletion/service.py`; `apps/server/src/twobrain_rec_server/auth/account_closure.py`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: System operation actor reference, deletion epoch, late results, локальные/backup/provider/retained состояния, corporate чужие объекты сохраняются.
  - Зависимости: T013. Приёмка: AC-007, AC-033, AC-034, AC-036.

- [ ] T015 [US4] Проверить повтор, удаление и поздние результаты под гонками. Пути: `apps/server/tests/integration/test_system_admin_recovery_deletion.py`.
  - Результат: Duplicate request/worker restart/revoke/delete-vs-export; old result доступен до новой публикации; один charge квоты; no resurrection.
  - Зависимости: T014. Приёмка: AC-012, AC-013, AC-033, AC-034, AC-036.

## US7

- [ ] T016 [US7] Добавить версии возможностей, цены и закреплённые условия подписки. Пути: `apps/server/src/twobrain_rec_server/db/models/billing.py`; `apps/server/src/twobrain_rec_server/db/migrations/versions/`; `apps/server/src/twobrain_rec_server/billing/catalog.py`.
  - Результат: Plans+prices, legacy IDs, exact snapshot pin, no latest fallback, month/year одна версия, capability allowlist, separate schedule/consent versions.
  - Зависимости: T007. Приёмка: AC-020, AC-021, AC-022, AC-041.

## US5

- [ ] T017 [US5] Реализовать общий расчёт прав, индивидуальные назначения и квоты. Пути: `apps/server/src/twobrain_rec_server/billing/admin_grants.py`; `apps/server/src/twobrain_rec_server/billing/entitlements.py`; `apps/server/src/twobrain_rec_server/billing/usage.py`; `apps/server/src/twobrain_rec_server/billing/storage.py`.
  - Результат: Adjustment ledger без fake invoice, precedence, exact limits/extra allocation, expiry сохраняет admitted reservations, no counter reset, timezones/calendar gifts.
  - Зависимости: T016. Приёмка: AC-016, AC-017, AC-018, AC-041.
  - В работе: общий resolver и ledger подключены к допуску/расходу обработки, хранению и странице использования. Единый расчёт показывает lifetime остатки дополнительных источников без сброса; профильные PostgreSQL/HTTP/browser проверки записаны в implementation-evidence.md. Остальные окна, lineage, исторический расход и все потребители ещё не завершены.

## US7

  - Дополнено: настоящие пользовательские/общие скачивания и экспорт ограничены resolver; точные форматы, повторный доступ к пакету, отзыв во время подготовки и временная граница выдачи аудио. Остальные consumers и полный lifecycle ещё открыты; см. implementation-evidence.md.

  - Обязательный открытый дефект actual-role проверки обмена: новое внутреннее приглашение не видит membership адресата (grantee_not_found). Требуются ограниченная проверка/поиск адресата и положительный HTTP-тест без обхода RLS; проверка новых коммерческих запретов не закрывает этот дефект.

- [ ] T018 [US7] Перевести покупку, продление и клиентов на произвольные поддерживаемые тарифы. Пути: `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`; `apps/server/src/twobrain_rec_server/billing/renewal_resolution.py`; `apps/server/src/twobrain_rec_server/billing/subscription.py`; `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`; `apps/server/src/twobrain_rec_server/api/auth.py`; `apps/server/src/twobrain_rec_server/public/offers.py`; `apps/server/src/twobrain_rec_server/billing/maintenance.py`.
  - Результат: Все consumers из research, новые plan codes без новых веток, legacy personal workspace kind сохраняется, renewal pinned version, общий lock order, durable dispatch claim до сети, crash takeover и no mixed old writers.
  - Зависимости: T017. Приёмка: AC-016, AC-017, AC-018, AC-019, AC-020, AC-021, AC-041.
  - В работе: подтверждение оплаты/продления выдаёт оплаченный произвольный код и точные pins, планирование и cutoff охватывают новые коды. Проверены month/year, old offer после закрытия продаж, повтор, несовпадение snapshots/schedule и actual app role. Формы выбора/покупки произвольного публичного тарифа подключены: точные условия и скидка проверяются перед счётом, повтор сравнивает исходную форму, закрытие продаж сериализуется с допуском. Остальные потребители, полный порядок блокировок и барьер старых writers ещё не завершены; evidence содержит команды и ограничения.

- [ ] T019 [US7] Добавить редактор, предпросмотр и публикацию тарифов. Пути: `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/plans.html`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: Draft/scheduled publish/sales stop/archive, exact scheduled approval включая authorizing grant ID/version/expiry, revoke/replacement/late execution tests, сравнение offers/влияния и уведомлений, optimistic version+row lock; старые подписчики не мигрируют автоматически.
  - Зависимости: T018. Приёмка: AC-020, AC-021, AC-022.

## US5

- [ ] T020 [US5] Добавить управление доступом, компенсациями и переходами подписки. Пути: `apps/server/src/twobrain_rec_server/billing/admin_grants.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/subscription.html`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: Preview денег/дат/доступа, superadmin-only fair_use.resolve с сохранением usage/referrals, sent/ambiguous reconcile gate, отмена только unsent, schedule version отдельно; transitions с notice/consent, limited batch<=100.
  - Зависимости: T018. Приёмка: AC-016, AC-017, AC-018, AC-019, AC-022, AC-037.

## US6

- [ ] T021 [US6] Показать историю оплат, чеков и возвратов с денежной сверкой. Пути: `apps/server/src/twobrain_rec_server/billing/history.py`; `apps/server/src/twobrain_rec_server/billing/reconciliation.py`; `apps/server/src/twobrain_rec_server/system_admin/queries.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/payments.html`.
  - Результат: Payer totals verified money only, no paid status patch, gift не revenue, receipt/provider refs masked; call existing reconciliation.
  - Зависимости: T018. Приёмка: AC-006, AC-015, AC-019.

## US5

- [ ] T022 [US5] Проверить тарифы, деньги, подарок и квоты на полном жизненном цикле. Пути: `apps/server/tests/integration/test_system_admin_billing.py`; `apps/server/tests/contract/test_system_admin_entitlements.py`.
  - Результат: Unknown plan code lifecycle, Jan31/Feb29/DST, grandfathering, lost response/double webhook/gift-vs-renewal, 18000→24000 quota, consent and snapshots immutable; pause-after-dispatch-claim, crash-before/after-send и fair_use resolve replay/race.
  - Зависимости: T019,T020,T021. Приёмка: AC-015, AC-016, AC-017, AC-018, AC-019, AC-020, AC-021, AC-022, AC-041.

## US8

- [ ] T023 [US8] Добавить версии акций, партии кодов и точный учёт резервов. Пути: `apps/server/src/twobrain_rec_server/db/models/billing.py`; `apps/server/src/twobrain_rec_server/db/migrations/versions/`; `apps/server/src/twobrain_rec_server/billing/promotions.py`.
  - Результат: New reservation per attempt, canonical identity, percent/gift budget units, locked count+budget, nullable invoice for gift, legacy trigger/counter reconciliation.
  - Зависимости: T022. Приёмка: AC-023, AC-024, AC-025, AC-026, AC-041.

- [ ] T024 [US8] Подключить акции и подарочные коды к покупке и назначениям. Пути: `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`; `apps/server/src/twobrain_rec_server/billing/promotions.py`; `apps/server/src/twobrain_rec_server/billing/admin_grants.py`.
  - Результат: Strict explicit code, one discount, eligibility повторная, sent reservation retained, gift+redemption одна tx, pause honors invoices, refunds no auto reuse.
  - Зависимости: T023. Приёмка: AC-023, AC-024, AC-025, AC-026, AC-027.

- [ ] T025 [US8] Добавить управление акциями и объяснимую статистику. Пути: `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/campaigns.html`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`; `apps/server/src/twobrain_rec_server/system_admin/queries.py`.
  - Результат: Draft/schedule/publish/pause/finish/archive; scheduled approval не зависит от natural browser expiry, revoke/изменение условий требует review; <=1000 codes one-time export, budgets, аудитории, dry eligibility, paid/gift/renewal/refund раздельно.
  - Зависимости: T024. Приёмка: AC-023, AC-024, AC-025, AC-026, AC-027.

- [ ] T026 [US8] Проверить конкурентные промокоды, бюджеты и миграцию кампаний. Пути: `apps/server/tests/integration/test_system_admin_promotions.py`.
  - Результат: Последний budget/code, retry после expired создаёт новую attempt, stale invoice after pause, merged identity, gift idempotency и refund restoration audited.
  - Зависимости: T025. Приёмка: AC-023, AC-024, AC-025, AC-026, AC-027, AC-041.

## US9

- [ ] T027 [US9] Добавить внутренние связи и историю обращений. Пути: `apps/server/src/twobrain_rec_server/db/models/support.py`; `apps/server/src/twobrain_rec_server/support/incidents.py`; `apps/server/src/twobrain_rec_server/support/redaction.py`; `apps/server/src/twobrain_rec_server/system_admin/queries.py`.
  - Результат: Local operation до meeting, verified link index, snapshots caps/retention, assignee/priority/status, внешняя safe схема неизменна.
  - Зависимости: T008. Приёмка: AC-011, AC-028, AC-029, AC-032, AC-040.

- [ ] T028 [US9] Добавить ограниченный приём и хранение технических событий. Пути: `apps/server/src/twobrain_rec_server/api/diagnostics.py`; `apps/server/src/twobrain_rec_server/observability/diagnostic_events.py`; `apps/server/src/twobrain_rec_server/db/migrations/versions/`.
  - Результат: Schema allowlist/version, dedup, server-assigned ownership, quotas/rate limits, event vs received time, loss counters и retention; no fake payment.
  - Зависимости: T027. Приёмка: AC-011, AC-028, AC-029, AC-032, AC-042.

- [ ] T029 [US9] Связать клиентские события, запись и очередь загрузки. Пути: `apps/macos/RecApp/Sources/Diagnostics/`; `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`; `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`; `apps/macos/Shared/Tests/SystemAdminDiagnosticsTests.swift`.
  - Результат: Полный event catalog, durable local ID, prelogin local only, account switch safety, bounded async queue, CPU/memory, видимый временный extended mode; no capture policy changes.
  - Зависимости: T028. Приёмка: AC-010, AC-011, AC-028, AC-029, AC-042.

- [ ] T030 [US9] Добавить карточку устройства и сквозную ленту проблемы. Пути: `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/device.html`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/incident.html`; `apps/server/tests/integration/test_system_admin_diagnostics.py`.
  - Результат: Source/freshness/unknown, related attempts и IDs, независимые upload/processing/content states, no assumed crash from interrupted session.
  - Зависимости: T029. Приёмка: AC-010, AC-011, AC-028, AC-029, AC-032, AC-042.

## US10

- [ ] T031 [US10] Реализовать каталог метрик и идемпотентные агрегаты. Пути: `apps/server/src/twobrain_rec_server/product_analytics/event_catalog.py`; `apps/server/src/twobrain_rec_server/product_analytics/retention.py`; `apps/server/src/twobrain_rec_server/observability/system_metrics.py`.
  - Результат: Все M01–M30, verified ledger money, consent/coverage/internal exclusion, cohort lag, small groups, late correction, no double milestones; readiness gate не обходить.
  - Зависимости: T026,T028. Приёмка: AC-027, AC-028, AC-030, AC-031, AC-042.

- [ ] T032 [US10] Добавить обзор и статистику с понятной детализацией. Пути: `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/overview.html`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/metrics.html`; `apps/server/tests/integration/test_system_admin_metrics.py`.
  - Результат: Period/timezone/definition/sample/coverage, unavailable !=0, scoped drilldown, no content for analyst, formulas synthetic expected values; W4 на 35/42-й день, late events и две оплаты одного payer в M27.
  - Зависимости: T031. Приёмка: AC-027, AC-030, AC-031, AC-038, AC-042.

## US11

- [ ] T033 [US11] Добавить диагностику интеграций, обмена, форматов и рефералов. Пути: `apps/server/src/twobrain_rec_server/system_admin/queries.py`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`; `apps/server/src/twobrain_rec_server/billing/referral_rewards.py`.
  - Результат: Calendar retry/disconnect, notifications.retry с delivery/revoked guards, revoke shared access, format context content permission, account merge blockers, referral lineage; no provider consent fabrication or prompt editor.
  - Зависимости: T015,T022,T027. Приёмка: AC-013, AC-014, AC-040.

## US12

- [ ] T034 [US12] Добавить инциденты, оповещения, зависимости и эксплуатационные настройки. Пути: `apps/server/src/twobrain_rec_server/observability/system_alerts.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/operations.html`; `apps/server/src/twobrain_rec_server/system_admin/operations.py`.
  - Результат: Dedup ack/assignee/resolution; configured delivery only, единый key-level settings allowlist (контакты/получатели из справочника, export ceiling, перспективный diagnostic retention), superadmin queue.pause/resume<=60min с auto-expiry и dispatch-race tests, storage/custody/provider/backup/restore provenance; no shell/secrets.
  - Зависимости: T030,T032. Приёмка: AC-032, AC-035, AC-036, AC-042.

- [ ] T035 [US12] Добавить защищённый аудит и ограниченные выгрузки таблиц. Пути: `apps/server/src/twobrain_rec_server/system_admin/audit.py`; `apps/server/src/twobrain_rec_server/system_admin/templates/system_admin/audit.html`; `apps/server/tests/integration/test_system_admin_audit_exports.py`.
  - Результат: 10k/24h limits, dataset permissions at generation/download, safe CSV, immutable audit, no raw codes/content, batch results only failed retry.
  - Зависимости: T009,T025,T032,T034. Приёмка: AC-036, AC-037, AC-039.

## Итоговая проверка

- [ ] T036 Проверить доступность и все основные маршруты в браузере. Пути: `apps/server/tests/e2e/test_system_admin_console.py`; `specs/254-system-admin-console/quickstart.md`.
  - Результат: Keyboard/200%/1024 и narrow read mode, focus/dialog/conflict, no-store/CSP/CSRF, 10 synthetic support cases <=2min.
  - Зависимости: T035,T033. Приёмка: AC-001, AC-004, AC-005, AC-006, AC-008, AC-009, AC-020, AC-023, AC-038, AC-039.

- [ ] T037 Доказать миграцию и безопасный откат на старых состояниях. Пути: `apps/server/tests/integration/test_system_admin_migration.py`; `apps/server/scripts/bootstrap_runtime_database_roles.py`; `specs/254-system-admin-console/contracts/migration.md`.
  - Результат: Все fixtures, backfill resume, no synthetic privileges, exact financial equality, promo counters, mixed-writer barrier + final catch-up до lag=0/counter equality, incompatible rollback blocked.
  - Зависимости: T026,T035. Приёмка: AC-003, AC-016, AC-018, AC-019, AC-021, AC-024, AC-025, AC-026, AC-033, AC-041.

- [ ] T038 Проверить нагрузку, отказ телеметрии и изоляцию пользовательского потока. Пути: `apps/server/tests/performance/test_system_admin_load.py`; `apps/macos/Shared/Tests/SystemAdminDiagnosticsTests.swift`; `specs/254-system-admin-console/quickstart.md`.
  - Результат: 10k/100k/1M,20 sessions,p95 targets;60min outage; source freshness <=15s/5min, CPU/memory gate, slow reports не блокируют запись.
  - Зависимости: T036,T037. Приёмка: AC-029, AC-031, AC-035, AC-042.

- [ ] T039 Завершить приёмку, convergence и подготовку выпуска. Пути: `specs/254-system-admin-console/tasks.md`; `specs/254-system-admin-console/quickstart.md`; `changes/unreleased/254-system-admin-console.md`.
  - Результат: Все FR/SC/AC evidence, reviewers gates, narrow domain suites, governance-fast exact SHA, applicable fast/full; русский changelog, migration limits и отдельное approval на commit/release. Не отмечать до выполнения.
  - Зависимости: T038. Приёмка: AC-001, AC-002, AC-003, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-012, AC-013, AC-014, AC-015, AC-016, AC-017, AC-018, AC-019, AC-020, AC-021, AC-022, AC-023, AC-024, AC-025, AC-026, AC-027, AC-028, AC-029, AC-030, AC-031, AC-032, AC-033, AC-034, AC-035, AC-036, AC-037, AC-038, AC-039, AC-040, AC-041, AC-042.

## Порядок и независимая проверка

US1 — обязательный фундамент. После T007 можно вести ветвь пользователей/встреч (T008–T015), billing (T016–T026) и диагностику (T027–T032) параллельно при разных владельцах файлов. Shared `operations.py`, `queries.py`, models и migration heads изменять последовательно/согласованно: маркер [P] намеренно не выдан задачам с общими файлами. T033–T035 объединяют домены. T036–T039 — общие gates.

Каждая US имеет собственные AC и тестовые задачи: US1 T007; US2 T036; US3 T012; US4 T015; US5/6/7 T022; US8 T026; US9 T030; US10 T032; US11 T033 + T036; US12 T035/T038. Наборы тестов надо сначала сделать падающими на отсутствующем/неверном поведении, затем реализовать соответствующий сервис; выделенная тестовая задача закрепляет итоговую доменную проверку, а не разрешает писать проверки после всей фичи.

Первый внутренний проверяемый срез: T001–T015. Он ещё не выполняет весь запрос владельца; billing/тарифы/акции и статистика обязательны до объявления Feature 254 завершённой.

## Покрытие требований задачами

Маппинг использует нормативные AC; широкая финальная T039 не заменяет конкретного владельца реализации.

| Требование | Задачи реализации / проверки |
|---|---|
| FR-001 | T002, T004, T005, T006, T007, T036 |
| FR-002 | T005, T006, T007 |
| FR-003 | T002, T005, T006, T007, T037 |
| FR-004 | T002, T005, T006, T007, T037 |
| FR-005 | T003, T005, T006, T007, T011, T012, T036 |
| FR-006 | T003, T005, T006, T007, T011, T012, T036 |
| FR-007 | T003, T005, T006, T007, T011, T012, T036 |
| FR-008 | T002, T004, T005, T006, T007, T036 |
| FR-009 | T002, T003, T005, T006, T007, T011, T012, T014, T015, T034, T035, T036 |
| FR-010 | T002, T003, T005, T006, T007, T011, T012, T014, T015, T034, T035, T036 |
| FR-011 | T002, T004, T005, T006, T007, T036 |
| FR-012 | T008, T036 |
| FR-013 | T008, T009, T021, T036 |
| FR-014 | T008, T009, T021, T036 |
| FR-015 | T008, T009, T014, T015, T021, T036 |
| FR-016 | T006, T009, T014, T015 |
| FR-017 | T006, T009, T014, T015, T027, T033 |
| FR-018 | T004, T008, T010, T011, T012, T028, T029, T030, T031, T032, T034, T035, T036, T038 |
| FR-019 | T008, T010, T012, T036 |
| FR-020 | T008, T010, T011, T012, T035, T036 |
| FR-021 | T008, T010, T011, T012, T029, T030, T036 |
| FR-022 | T010, T011, T012, T036 |
| FR-023 | T010, T011, T012, T027, T028, T029, T030 |
| FR-024 | T010, T027, T028, T029, T030, T038 |
| FR-025 | T003, T010, T011, T012, T013, T015, T029, T030 |
| FR-026 | T003, T010, T011, T012, T013, T015, T036 |
| FR-027 | T003, T013, T015 |
| FR-028 | T010, T011, T012, T013, T015, T033 |
| FR-029 | T009, T027, T033 |
| FR-030 | T009, T010, T011, T012, T013, T015, T027, T033, T036 |
| FR-031 | T021, T022 |
| FR-032 | T021, T022 |
| FR-033 | T018, T020, T021, T022, T037 |
| FR-034 | T017, T018, T020, T022, T037 |
| FR-035 | T017, T018, T020, T022, T023, T024, T025, T026, T037 |
| FR-036 | T006, T009, T014, T017, T018, T020, T022, T037 |
| FR-037 | T009, T018, T020, T021, T022, T027, T033, T037 |
| FR-038 | T017, T018, T020, T022 |
| FR-039 | T017, T018, T020, T022, T037 |
| FR-040 | T009, T018, T020, T021, T022, T027, T033, T037 |
| FR-041 | T002, T004, T007, T016, T017, T018, T019, T022, T023, T026, T036, T037 |
| FR-042 | T016, T018, T019, T022, T036 |
| FR-043 | T016, T018, T019, T022, T036 |
| FR-044 | T002, T004, T007, T016, T017, T018, T019, T022, T023, T026, T037 |
| FR-045 | T016, T018, T019, T020, T022, T037 |
| FR-046 | T016, T018, T019, T022, T037 |
| FR-047 | T002, T004, T007, T016, T017, T018, T019, T022, T023, T026, T036, T037 |
| FR-048 | T002, T004, T007, T016, T017, T018, T020, T022, T023, T026, T037 |
| FR-049 | T002, T004, T007, T016, T017, T018, T019, T020, T022, T023, T026, T037 |
| FR-050 | T016, T018, T019, T020, T022, T037 |
| FR-051 | T023, T024, T025, T026, T036 |
| FR-052 | T023, T024, T025, T026, T036, T037 |
| FR-053 | T023, T024, T025, T026, T036, T037 |
| FR-054 | T023, T024, T025, T026, T036, T037 |
| FR-055 | T023, T024, T025, T026, T036 |
| FR-056 | T003, T023, T024, T025, T026, T037 |
| FR-057 | T003, T023, T024, T025, T026, T037 |
| FR-058 | T003, T023, T024, T025, T026, T037 |
| FR-059 | T023, T024, T025, T026, T037 |
| FR-060 | T024, T025, T026, T031, T032 |
| FR-061 | T010, T027, T028, T029, T030 |
| FR-062 | T010, T027, T028, T029, T030, T034 |
| FR-063 | T010, T027, T028, T029, T030, T038 |
| FR-064 | T027, T028, T029, T030, T031 |
| FR-065 | T004, T008, T027, T028, T029, T030, T031, T032, T034, T038 |
| FR-066 | T004, T008, T027, T028, T029, T030, T031, T032, T034, T038 |
| FR-067 | T024, T025, T026, T031, T032, T038 |
| FR-068 | T024, T025, T026, T031, T032, T038 |
| FR-069 | T027, T028, T030, T034 |
| FR-070 | T027, T028, T030, T034 |
| FR-071 | T003, T006, T009, T013, T014, T015, T037 |
| FR-072 | T003, T009, T013, T014, T015, T037 |
| FR-073 | T003, T013, T014, T015, T037 |
| FR-074 | T003, T013, T014, T015, T037 |
| FR-075 | T004, T034, T038 |
| FR-076 | T009, T027, T033 |
| FR-077 | T004, T034, T038 |
| FR-078 | T004, T010, T011, T012, T013, T015, T033, T034, T038 |
| FR-079 | T004, T034, T038 |
| FR-080 | T002, T003, T007, T011, T014, T015, T034, T035 |
| FR-081 | T003, T009, T013, T015, T016, T017, T018, T019, T020, T022, T035, T037 |
| FR-082 | T003, T009, T020, T035 |
| FR-083 | T003, T009, T020, T035 |
| FR-084 | T008, T032, T036 |
| FR-085 | T004, T008, T028, T029, T030, T031, T032, T034, T036, T038 |
| FR-086 | T008, T010, T011, T012, T035, T036 |
| FR-087 | T008, T010, T011, T012, T027, T028, T029, T030, T031, T035, T036 |
| FR-088 | T002, T003, T007, T011, T014, T015, T034, T035 |
| FR-089 | T004, T008, T027, T028, T029, T030, T031, T032, T034, T038 |
| FR-090 | T002, T004, T005, T006, T007, T016, T017, T018, T022, T023, T026, T036, T037 |

## Покрытие измеримых целей

| Цели | Задачи |
|---|---|
| SC-001 | T008, T027, T030, T036 |
| SC-002, SC-003 | T002–T007, T011–T012, T035 |
| SC-004, SC-005, SC-011 | T013–T026 |
| SC-006, SC-007, SC-009 | T028–T032, T034, T038 |
| SC-008 | T031–T032 |
| SC-010 | T036 |
| SC-012 | T016, T023, T037 |

GitHub-связи находятся в [issues.md](issues.md); tasks.md остаётся источником состояния реализации.
