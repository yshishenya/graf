# Tasks: F258 — готовность встречи и уведомления

Input: spec.md, plan.md, research.md, data-model.md, contracts/progress.md, quickstart.md.
Umbrella: https://github.com/yshishenya/graf/issues/6818.

## Phase 1 — Подготовка

- [X] T001 Принять reviewer checklist и analyze, синхронизировать ownership в `specs/258-meeting-progress-recovery/tasks.md`. [FR-001–012]

## Phase 2 — Общие состояния

- [X] T002 Добавить регрессии empty slot/pending/partial/stale lineage в `apps/server/tests/integration/test_meeting_summary_slots.py` и `tests/contract/test_processing_status_contract.py` перед исправлением. [FR-001–003]
- [X] T003 Исправить выбор audio revision в `apps/server/src/twobrain_rec_server/cabinet/egress.py` и общую summary projection в `outcomes/progress.py`, `processing/status.py`; сохранить published source/access/deletion fences. [FR-001–003]

## Phase 3 — US1: открытая встреча

Independent test: звук и transcript доступны до итогов; итог появляется автоматически в web/WKWebView без сброса player/draft.

- [X] T004 [US1] Добавить Node поведенческие регрессии в `apps/server/tests/unit/test_meeting_progress_ui.py`: долгий pending, сеть, partial, selected format, stale response и safe navigation. [FR-004–005]
- [X] T005 [US1] Исправить polling/fragment refresh/summary navigation и понятные статусы в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, `cabinet/view_models.py`, `cabinet/queries.py`, `cabinet/rendering.py` и `cabinet/templates/cabinet/pages/meeting_detail_content.html`, включая список. [FR-002–005/011; SC-001–003/005]

## Phase 4 — US2: native путь

Independent test: synthetic capture start/Stop→transcript→summary с закрытым главным окном, одна допустимая доставка.

- [X] T006 [US2] Добавить sync/model/notification регрессии в `apps/server/tests/integration/test_recording_sync_processing.py` и `apps/macos/Shared/Tests/DesktopNotificationControlTests.swift`, `DesktopUploadQueueV5Tests.swift` перед кодом. [FR-006–009]
- [X] T007 [US2] Передать summary metadata через `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`, `api/schemas.py`, `apps/macos/Shared/Sources/Models/AudioModelCore.swift` и `RecApp/Sources/Upload/DesktopUploadClient.swift`, продолжить существующий follow-up в `DesktopUploadQueueService.swift`. [FR-003–004/007/009]
- [X] T008 [US2] Связать подтверждённый start/Stop и recap, owner/epoch/permission/visibility в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`, `DesktopControlPanel.swift`, `RecApp/App/TwoBrainRecApp.swift` и `Sources/Calendar/CalendarTray.swift`; доступный ask UI, настройки, F255 menu без регресса. [FR-006–009/011; SC-004–005]

## Phase 5 — US3: восстановление

Independent test: свежие инциденты разных записей не теряются; worker wake работает от узкой media role.

- [X] T009 [US3] Дополнить регрессии инцидентов/retention/recovery и media-role в `apps/macos/Shared/Tests/DesktopNotificationControlTests.swift`, `apps/server/tests/integration/test_playback_normalization_postgres.py` и `tests/unit/test_playback_normalization_worker.py`. [FR-010/012]
- [X] T010 [US3] Исправить per-recording incidents/reconciliation в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`; metadata-only wake в `apps/server/src/twobrain_rec_server/normalization/worker.py` и минимальные grants в `apps/server/scripts/bootstrap_runtime_database_roles.py`/соответствующей test fixture. [FR-010/012]

## Phase 6 — Проверка и PR

- [ ] T011 Пройти `specs/258-meeting-progress-recovery/quickstart.md`, code/Ponytail review, converge и high-risk проверки; записать PASS/FAIL/SKIPPED в `specs/258-meeting-progress-recovery/evidence.md`, добавить `changes/unreleased/F258.yaml`, commit/push/PR и exact-SHA governance-fast. Релиз/merge/deploy исключены. [SC-001–005]

## Dependencies & Execution Order

T001 → T002 → T003; T004 до T005, T006 до T007–T008, T009 до T010; T011 после всех. US1 и native regression research могут проверяться раздельно, но общий API/Swift glue правится последовательно. [P] не используется: shared notification и JS файлы имеют одного writer.

## Implementation Strategy

Сначала доказать исправление audio/summary projection (минимальный полезный результат), затем web auto-update, native readiness и incident recovery. Каждый блок имеет регрессии до кода. Независимо проверяемые блоки сходятся в одном PR; нет промежуточного релиза.

## GitHub ownership

T001 — #6818; T002–T003 — #6819; T004–T005 — #6820; T006–T008 — #6821; T009–T010 — #6822; T011 — #6823. Все открыты на 2026-09-08. Старые F239/F249 issues связаны как context, не закрываются автоматически.

## Phase 7: Convergence

- [ ] T012 После освобождения общего GRAF Dev пройти установленную приёмку exact SHA через штатный harness: start/Stop → transcript → summary, OS banner/Focus/denied, keyboard/focus/200%/themes и сохранение player/draft; записать независимые PASS/FAIL в `specs/258-meeting-progress-recovery/evidence.md` по SC-003–005, US2/AC1–4 (partial, HIGH). Общая ownership с T011: #6823; занятый стенд F256/F257 и более новая схема не обходятся. До этой проверки PR остаётся draft.
