# Tasks: F297 — Непрерывная запись, честное хранение и правдивые обещания запуска

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Lane**: high-risk-product. Base `e7723baf8a6890fff54956007baa0b29b3047892`. Umbrella #8123.

## Phase 1 — Setup and gates

- [X] T001 Зафиксировать F297, umbrella #8123, spec/plan/research/contracts/checklists/quickstart и провести независимый reviewer-owned checklist review до кода. (Issue #8123)
- [X] T002 Добавить `changes/unreleased/F297.yaml` с русским описанием изменений и границ. (Issue #8123)

## Phase 2 — US1: запись продолжается при смене устройства и коротком разрыве

- [X] T003 [US1] Добавить RED-тесты в `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`: короткий system-audio gap 5–20 мс и ровно 500 мс закрываются тишиной и не дают `renderReferenceMissing`; gap 500 мс–15 с не маскируется и даёт partial/stop; gap выше `maximumKnownGapSeconds` остаётся `gapExceedsBound`; microphone gap остаётся fail-closed. (Issue #8123)
- [X] T004 [US1] Реализовать bridge короткого system-audio gap в `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift` с отдельным `maximumBridgedGapSeconds = 0.5`; добавить счётчики `continuityGapBridgedFrames`/`continuityRouteChangeCount` в `RecordingAudioTimelineMetrics` и diagnostics без аудио/путей. (Issue #8123)
- [X] T005 [US1] Добавить RED-тесты в `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift` на `.routeChanged` + новый `routeGeneration` с PTS, начинающимся с нуля: одна запись, без обрезки новых кадров, без `routeGenerationChanged`. (Issue #8123)
- [X] T006 [US1] Реализовать route rebase в `RecordingAudioTimeline.swift`: разрешить смену generation после `.routeChanged`, вычислить per-source offset и начать новый сегмент с `lastInputEndFrame`; сбросить converter/inputFormat при смене sample rate; сохранить fail-closed для `.sourceStopped`/`.dropped`. (Issue #8123)
- [X] T007 [US1] Добавить RED→GREEN тест на частичную запись в `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`: при непреодолимом continuity-сбое writer сохраняет playable prefix, ставит `partialContinuity=true` и `failureReason=timelineMisaligned`, очередь разрешает upload. (Issue #8123)
- [X] T008 [US1] Реализовать partial fallback в `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`, `LocalRecordingManifestService.swift` и `apps/macos/Shared/Sources/Models/AudioModelCore.swift`; добавить аддитивные optional-поля manifest, неблокирующий доступный статус в `CaptureControlViewCore.swift` (роль status/alert, VoiceOver, клавиатура, без перехвата фокуса). (Issue #8123)
- [X] T009 [US1] Обновить существующие тесты/ContractValidation, которые ожидали `renderReferenceMissing`/`captureFailed` на коротком gap; сохранить проверки реальной потери и AEC3. (Issue #8123)
- [ ] T010 [US1] Прогнать focused Swift: `swift build`, `swift test --filter 'RecordingAudioTimeline|LocalRecordingWriterSystemAudio|SystemAudioCaptureService'`, `swift run ContractValidation`; выполнить QA-матрицу `quickstart.md` §1 на реальном Mac (AirPods, проводные наушники, док/дисплей, смена до первого пакета, сон/крышка, короткий реальный звонок); записать metadata-only evidence в `validation.md`. (Issue #8123)

## Phase 3 — US2: retention 365 дней и backup 30 дней исполняются

- [X] T011 [US2] Добавить RED-тест `apps/server/tests/unit/test_retention_reconciler.py`: перебирает активные workspace, вызывает существующий `run_retention_scan`, изолирует ошибку workspace, не дублирует deletion request при повторе. (Issue #8123)
- [X] T012 [US2] Добавить `retention_scan` в `ALLOWED_MAINTENANCE_OPERATIONS` (`apps/server/src/twobrain_rec_server/db/tenant_context.py`), аддитивную migration `0114_retention_scan_maintenance.py` для `rec_maintenance_allowed()` и согласовать runtime bootstrap с обеими версиями helper; реализовать `run_retention_reconciler` в `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py` с суточным интервалом, bounded batch, opt-in выключателем `TWOBRAIN_RETENTION_SCHEDULER_ENABLED` (default `false`) и включением только после dry-run и проверенной резервной копии. (Issue #8123)
- [X] T013 [US2] Добавить `infra/scripts/prune-rec-backups.sh` с dry-run по умолчанию, `--execute`, `--older-than-days`, `--backup-root`/`TWOBRAIN_BACKUP_ROOT`, строгим именем каталога, запретом symlink/чужих путей, metadata-only output и exit codes 0/2/3; добавить focused Python/shell test. (Issue #8123)
- [X] T014 [US2] Добавить `infra/systemd/graf-rec-backup-prune.service` и `.timer`, `docs/runbooks/backup-retention.md` с install/enable/disable/rollback; production install/execute оставить операторским. (Issue #8123)
- [X] T015 [US2] Обновить `apps/server/src/twobrain_rec_server/public/templates/public/privacy.html` и `docs/agent-guidance/release-and-validation.md`: сроки совпадают с ежедневным retention после явного включения оператором и операторским prune; убрать безусловные обещания, если scheduler выключен; добавить disable/rollback. (Issue #8123)
- [X] T016 [US2] Прогнать focused server/script validation: retention tests, prune dry-run + temp-dir execute, bootstrap после migration, `git diff --check`; записать evidence в `validation.md`. (Issue #8123)

## Phase 4 — US3: оферта и checkout говорят правду

- [X] T017 [US3] Добавить/обновить contract tests в `apps/server/tests/contract/test_billing_clarity.py`, `test_billing_purchase_ui.py` и public template tests: автопродление checked/not required, оферта говорит «включено по умолчанию», лимит 4 часа, нет «без ограничения длительности»; отдельный тест подтверждает неизменность routes/CSRF/auth/form method/quote/offer consent. (Issue #8123)
- [X] T018 [US3] Обновить `apps/server/src/twobrain_rec_server/public/templates/public/offer.html`, `landing.html` и `billing_checkout_content.html` только в текстовой части; код автопродления оставить checked, CSRF/auth/форму не менять. (Issue #8123)
- [ ] T019 [US3] Прогнать focused render/browser checks для `/offer`, `/` и `/billing/checkout`; записать evidence. (Issue #8123)

## Phase 5 — US4: referral без 500

- [X] T020 [US4] Добавить RED-тест `apps/server/tests/unit/test_referral_landing.py`: рендер referral без `public_analytics` не падает, валидный токен 200, неизвестный/истёкший 410, недоступная БД 503. (Issue #8123)
- [X] T021 [US4] Исправить `cabinet/auth/analytics.html` безопасным default и передать `public_analytics` из `referrals.py`; сохранить StrictUndefined. (Issue #8123)
- [ ] T022 [US4] Проверить live `/r/<unknown>` и `/referral/<unknown>` → 410, не 500; отдельно проверить 503 как состояние недоступности; записать evidence. (Issue #8123)

## Phase 6 — Convergence and release gates

- [ ] T023 Сверить spec/plan/tasks/contracts с реализацией, обновить `validation.md`, выполнить `$speckit-converge`, проверить `legacy_new=0`, `unowned_legacy=0`, `expired_exceptions=0`. (Issue #8123)
- [ ] T024 Подготовить PR с русским описанием, получить exact-SHA `governance-fast`, `macos-pr`, `pr-metadata` и один `release-full` на frozen candidate; production retention/prune enablement — отдельное действие после dry-run и проверенной резервной копии. (Issue #8123)

## Dependencies

T001 → T002 → T003–T010 (US1) and T011–T016 (US2) and T017–T019 (US3) and T020–T022 (US4) → T023 → T024.

US1 and US2 touch different surfaces and can run in parallel after T001. US3/US4 are small and can run in parallel with US1/US2. Do not run two writers on the same file.
