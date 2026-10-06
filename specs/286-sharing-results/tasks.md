# Tasks: Передача итогов и управляемая автоотправка

**Input**: `specs/286-sharing-results/{spec,plan,research,data-model,quickstart}.md`, `contracts/sharing.md`.
**Lane**: high-risk-feature; sensitive regression tests precede implementation. All implementation waits for independent review, analyze and issue sync.

## Phase 1 — Preparation

- [X] T001 Зафиксировать проверенные требования, независимое ревью, анализ и связь задач GitHub в `specs/286-sharing-results/{review-report,analysis,tasks}.md` (FR-001–024). (Issue #7547)

## Phase 2 — Foundation

- [X] T002 Проверить миграцию, tenant-bound данные и runtime RLS в `apps/server/tests/integration/test_summary_sharing.py` и `test_summary_autosend.py` до реализации; реализовать additive модели публикации/пакета/адресата/отписки в `apps/server/src/twobrain_rec_server/db/models/summary_sharing.py`, предпочтения/правила в `summary_autosend.py`, регистрацию в `db/models/__init__.py` и миграции в `apps/server/src/twobrain_rec_server/db/migrations/versions/`; unique пакет workspace+owner+idempotency_key, адресат batch+address_hash, preference workspace+owner; default ask_enabled true / paused false, AUTO выключен (FR-009,012,020). (Issue #7548)

## Phase 3 — US1 Ссылка (P1)

Independent test: one copy and repeat preserve address/document/expiry; new current summary and title do not alter publication; revoke/deletion immediately deny reading.

- [X] T003 [US1] Добавить тесты stable link, allowlist, superseded, rotate/revoke, ACL/expiry/deletion в `apps/server/tests/integration/test_summary_sharing.py` и сохранить legacy regression `test_recording_share_public_link.py` (FR-002–007,020,021). (Issue #7549)
- [X] T004 [US1] Реализовать сохранённую проекцию и recoverable encrypted link в `apps/server/src/twobrain_rec_server/cabinet/summary_sharing.py`, nullable grant/invitation additions в `db/models/meeting_access.py`, явные операции с expected version в `api/summary_sharing.py`; варианты срока 7/30/90, default30, legacy без ciphertext → replacement_required (FR-002–007). (Issue #7550)
- [X] T005 [US1] Подключить saved projection к HTML/JSON public/authorized read в `apps/server/src/twobrain_rec_server/api/cabinet.py`, проверить ingress limiter/log masking и no-store/no-referrer/noindex success/error в `apps/server/src/twobrain_rec_server/main.py` и инфраструктурных конфигурациях `infra/` (FR-020,021). (Issue #7551)
- [X] T006 [US1] Заменить окно на «По ссылке» / «По почте», выбранный формат, предпросмотр, copy/fallback и explicit link actions в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html`, `cabinet/static/cabinet/summary-sharing.js`, `cabinet/static/cabinet/cabinet.css`; исключить двойной обработчик в `cabinet.js`, подключить asset в `templates/cabinet/base.html` (FR-001–005,022). (Issue #7552)

## Phase 4 — US2 Почта (P1)

Independent test: staged recipients give no access/mail; double submit one immutable batch; success/known failure/unknown distinct; forwarding cannot authenticate recipient.

- [X] T007 [US2] Добавить тесты immutable batch, max50, idempotency conflict, independent email login/accept и known failure/unknown crash/retry в `apps/server/tests/integration/test_summary_sharing.py` и `test_summary_delivery.py` до реализации (FR-008–011,019). (Issue #7553)
- [X] T008 [US2] Реализовать batch/recipient ledger, real-device manual limits, exact verified identity, separate invitation/read expiry, saved publication accept в `apps/server/src/twobrain_rec_server/cabinet/summary_sharing.py`, `cabinet/access.py`, `api/summary_sharing.py`; убрать bearer session bootstrap всех непринятых приглашений из `cabinet/web_routes/browser.py`, сохранив full ACL старых прав (FR-008–011). (Issue #7554)
- [X] T009 [US2] Реализовать SummaryDeliveryWorkflow, bounded DispatchIntent recovery, commit sending before network и unknown без replay в `apps/server/src/twobrain_rec_server/workflows/summary_delivery.py`, регистрацию в `workflows/worker.py`, recovery в `workflows/maintenance_worker.py`, maintenance scope в `db/tenant_context.py`; использовать существующий Postal, network вне transaction (FR-009,011,019). (Issue #7555)
- [X] T010 [US2] Реализовать точные выбранные адреса, сохранённый ключ double-submit/lost reply, возобновление status, retry только failed и простой итог «Итоги отправлены»/«Готово» в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/summary-sharing.js`; server form fallback в `api/summary_sharing.py` (FR-008–011,022). (Issue #7556)

## Phase 5 — US3 Автоотправка (P1)

Independent test: ASK silent, explicit meeting/series authority, +5min/ready+24h, fresh complete internal roster; pause/cancel/restart/source change and duplicate recorders cannot duplicate disclosure.

- [X] T011 [US3] Добавить проверки ready/delay/deadline, roster/identity/source/privacy/conflict, pause epoch, future-only series, duplicate occurrence, suppression и cancellation race в `apps/server/tests/integration/test_summary_autosend.py`, нормализацию полноты в `tests/unit/test_calendar_normalization.py` до реализации (FR-012–019). (Issue #7557)
- [X] T012 [US3] Реализовать owner preferences/version/auto_epoch, meeting/series rules и guard_auto_batch в `apps/server/src/twobrain_rec_server/cabinet/summary_autosend.py`, `api/summary_autosend.py`; сохранять attendeesOmitted/completeness в `calendar/google.py`; exact series_key, active verified WorkspaceMembership, <=15min complete Google snapshot/organizer.self, unknown/external/new/declined/private/conflict → requires_review; max50 и отдельный bounded owner budget (FR-012–019). (Issue #7558)
- [X] T013 [US3] Подключить atomic readiness hook в `apps/server/src/twobrain_rec_server/outcomes/ai_service.py` и ограниченное recovery в `workflows/maintenance_worker.py`; pending batch не создаёт доступ, guard до каждого recipient sending, unique initial occurrence вне rule version, ready+5min/ready+24h и no history resurrection (FR-013–019). (Issue #7559)
- [X] T014 [US3] Добавить раздел «Отправка участникам» в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html`, per-meeting controls/ASK/queue/cancel и exact scope/recipients в `fragments/meeting_share.html`, `pages/meeting_detail_content.html`, `cabinet/static/cabinet/summary-sharing.js`; проверить `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` без изменения бинарника при существующем разрешённом маршруте (FR-012–019,022). (Issue #7560)

## Phase 6 — US4 Польза получателю (P2)

Independent test: anonymous summary first; own-meeting CTA cannot join author workspace; GET optout inert, POST stops AUTO only.

- [X] T015 [US4] Реализовать scoped optout GET/POST и тест scanner-safe suppression в `apps/server/src/twobrain_rec_server/api/summary_sharing.py`, `cabinet/summary_sharing.py`, `tests/integration/test_summary_delivery.py`; один добровольный «Начать со своей встречи» после документа в `cabinet/templates/cabinet/pages/shared_meeting_summary_content.html` и own-workspace route rendering в `cabinet/rendering.py`; no analytics/email/token leak (FR-007,019,021,023,024). (Issue #7561)

## Phase 7 — Integration, validation and production

- [X] T016 Подключить routers в `apps/server/src/twobrain_rec_server/main.py`, cleanup snapshot/ciphertext/address/cancel intents в `deletion/service.py`; проверить runtime-role RLS, deletion/revoke races и legacy ACL в `apps/server/tests/integration/test_summary_sharing.py`, `test_recording_workflow_deletion_races.py`; добавить feature fragment `changes/unreleased/F286.yaml` (FR-020,024). (Issue #7562)
- [X] T017 Проверить actual UI/no-JS 320/390 обе темы и keyboard/focus, tests по `specs/286-sharing-results/quickstart.md`, независимое code/security review и convergence; записать concrete source/evidence в `specs/286-sharing-results/validation.md`, дополнительные обязательные задачи только append (FR-001–024, SC-001–005). (Issue #7563)
- [ ] T018 Выполнить exact-SHA governance-fast/macos-pr/pr-metadata, merged CalVer release/train freeze, один authoritative release-full, CD dry-run/execute, public health/synthetic feature smoke; сохранить macOS installer/appcast, tag/GitHub Release и tracker closeout в `specs/286-sharing-results/release-evidence.md` и release tooling `infra/scripts/{release-candidate,cd-remote}.sh`, `scripts/prepare-release.sh` (FR-024, high-risk-feature). (Issue #7564)

## Dependencies and ownership

## GitHub task links

T001: https://github.com/yshishenya/graf/issues/7547
T002: https://github.com/yshishenya/graf/issues/7548
T003: https://github.com/yshishenya/graf/issues/7549
T004: https://github.com/yshishenya/graf/issues/7550
T005: https://github.com/yshishenya/graf/issues/7551
T006: https://github.com/yshishenya/graf/issues/7552
T007: https://github.com/yshishenya/graf/issues/7553
T008: https://github.com/yshishenya/graf/issues/7554
T009: https://github.com/yshishenya/graf/issues/7555
T010: https://github.com/yshishenya/graf/issues/7556
T011: https://github.com/yshishenya/graf/issues/7557
T012: https://github.com/yshishenya/graf/issues/7558
T013: https://github.com/yshishenya/graf/issues/7559
T014: https://github.com/yshishenya/graf/issues/7560
T015: https://github.com/yshishenya/graf/issues/7561
T016: https://github.com/yshishenya/graf/issues/7562
T017: https://github.com/yshishenya/graf/issues/7563
T018: https://github.com/yshishenya/graf/issues/7564


T001 gates all code. T002 foundation precedes runtime integration and DB services; UI based on the reviewed API contract can be written in parallel but cannot be accepted before DB integration; sensitive tests precede corresponding implementation. Backend owns T003–005, T007–009 and backend portion T015; AUTO owns T011–013 and its model/migration; root owns T006,T010,T014 and integration T016–018. Only root edits shared model exports/main/worker registration/maintenance/deletion/templates/static. Backend edits access/browser/cabinet API. Migration chain coordinated: backend first, AUTO descendant. US2 uses US1 snapshot; US3 uses US2 queue; US4 uses saved reader.

Parallel examples after foundation: backend US1/US2 services; AUTO dedicated rules/guards/tests; root UI. No [P] marker on shared-file tasks. Independent reviewer touches only checklists/report before code and performs read-only code review after.

## Implementation strategy

Complete and validate US1, then recipient delivery/US2 and AUTO/US3 integration; all four stories remain required by user. Publish production only after all release gates. No new service/dependency or unrelated governance changes.

## Дополнительная проверка совместимости после реализации

- [X] T019 Сохранить граф опубликованных итогов при подтвержденном объединении аккаунтов: пять scoped FK `ON UPDATE CASCADE` в миграции 0104 и моделях, явный flush родительской встречи перед переносом metadata; реальная app-role регрессия проверяет RLS, документы, pending/accepted/unknown, историческое согласие и отмену неначатой доставки. Ранее отправленная ссылка с прежним workspace остается закрытой; владелец получает актуальную ссылку. Evidence: test_summary_sharing_account_merge.py, 53 passed related merge/delivery/deletion. (Issue #7566)

T019: https://github.com/yshishenya/graf/issues/7566

## Исправления полной проверки перед production

- [X] T020 Устранить замечания замороженной полной проверки: PostgreSQL-only миграция и typed revision declarations; орфография пользовательских текстов; актуальные проверки нового summary-only окна с сохранением клавиатуры/фокуса и закрытого аудио; подтвержденный независимый вход приглашения; актуальный inventory секрета maintenance/accepted summary slot и canonical OpenAPI. Старые полные права проверять через действующий API и реальный браузер, без восстановления удаленного выбора ролей в окне итогов. Отмененный кандидат не выпускать; после исправления создать новый замороженный кандидат и его единственную полную проверку. (Issue #7568)

T020: https://github.com/yshishenya/graf/issues/7568

## Очистка повторной production проверки

- [X] T021 (Issue #7573) Исправить порядок удаления storage_reservations перед track_artifacts в общем cleanup_smoke_artifacts.py; реальная PostgreSQL проверка должна удалять только выбранный синтетический граф, сохранять соседний и завершать очистку без FK отказа. Полная проверка и новый кандидат обязательны; прежний runtime не подменять локальным скриптом.
