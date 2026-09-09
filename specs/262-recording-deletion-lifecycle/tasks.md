# Tasks: F262 — Согласованная запись и удаление

Источник: spec.md, plan.md, contracts/lifecycle.md; high-risk-feature.

## Подготовка

- [X] T001 Проверить reviewer-owned требования и согласованность в specs/262-recording-deletion-lifecycle/checklists/security-ux.md и analysis.md. — issue #6876; PR #6911.

## Основа — идентичность, команда и запрет действий

- [X] T002 Добавить проверки долговечных команд, scope и приоритета удаления в apps/macos/Shared/Tests/RecordingDeletionLifecycleTests.swift. — issue #6877; PR #6911.
- [X] T003 Реализовать типизированное сохраняемое состояние операций и migration в apps/macos/Shared/Sources/Models/RecordingDeletionLifecycle.swift и AudioModelCore.swift. — issue #6878; PR #6911.
- [X] T004 Реализовать общие guards, durable intent, safe recovery и stale callback fence в apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift. — issue #6879; PR #6911.

## US1 — удалённая запись не возвращается

- [X] T005 [US1] Проверить и исправить terminal projection и local open guards в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift и Sources/Upload/DesktopUploadCustodyProjection.swift. — issue #6880; PR #6911.
- [X] T006 [US1] Сделать повторяемое серверное удаление и typed receipt через apps/server/src/twobrain_rec_server/cabinet/web_routes/deletion.py и api/cabinet.py с integration проверками. — issue #6881; PR #6911.

## US3 — загрузка, отсутствие сети и позднее создание

- [X] T007 [US3] Добавить PostgreSQL/RLS проверки cancel/create в apps/server/tests/integration/test_recording_origin_cancellation.py. — issue #6882; PR #6911.
- [X] T008 [US3] Реализовать origin cancellation модель/миграцию и общий create guard в apps/server/src/twobrain_rec_server/db и ingest/meetings.py. — issue #6883; PR #6911.
- [X] T009 [US3] Добавить owner-only cancellation endpoint и receipt в apps/server/src/twobrain_rec_server/api/ingest.py и deletion/origin_cancellation.py. — issue #6884; PR #6911.
- [X] T010 [US3] Реализовать typed delete/state adapters и выполнение очереди с retry/restart в apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift и DesktopUploadQueueService.swift. — issue #6885; PR #6911.

## US5 — удалённые устройства, очистка, доступ

- [X] T011 [US5] Проверить и реализовать late verified ACK и ensure-task в apps/server/src/twobrain_rec_server/deletion/local_purge.py и tests/integration/test_local_purge_coordination.py. — issue #6886; PR #6911.
- [X] T012 [US5] Реализовать bounded lifecycle lookup origins/meetings с текущими access guards в apps/server/src/twobrain_rec_server/ingest/desktop_sync.py и api adapters. — issue #6887; PR #6911.
- [X] T013 [US5] Подключить независимый deletion/purge цикл, scope и migration к apps/macos/RecApp/App/TwoBrainRecApp.swift. — issue #6888; PR #6911.

## US2/US4 — единая запись, выбор, плеер и результат

- [X] T014 [US2] Проверить mixed-list lifecycle и отсутствие дублей через apps/server/tests/browser/mixed-meeting-list.test.cjs. — issue #6889; PR #6911.
- [X] T015 [US2] Переработать identity/capability projection, фильтры и счётчики в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js и native bridge. — issue #6890; PR #6911.
- [X] T016 [US4] Подключить единые checkbox/bulk/per-item результаты и keyboard focus к cabinet.js и apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift. — issue #6891; PR #6911.
- [X] T017 [US2] Реализовать минимальный управляемый local player и отзыв session в apps/macos/RecApp/Sources/Cabinet/LocalRecordingPlayer.swift и App/TwoBrainRecApp.swift. — issue #6892; PR #6911.
- [X] T018 [US4] Добавить доступ к текущим операциям/существующим deletion reports через apps/server/src/twobrain_rec_server/cabinet и native projection. — issue #6893; PR #6911.

## Приёмка и завершение

- [X] T019 Проверить compatibility/legacy/rollback и 51 сценарий с результатами в specs/262-recording-deletion-lifecycle/quickstart.md и evidence.md. — issue #6894; PR #6911.
- [X] T020 Провести Ponytail review, converge, focused validation и добавить changes/unreleased/F262.yaml. — issue #6895; PR #6911.
- [X] T021 Пройти reviewer/code/PR governance-fast и необходимые installed-app/release gates с точным SHA; записать evidence в specs/262-recording-deletion-lifecycle/evidence.md. — issue #6896; PR #6911.

## Зависимости

T001 → T002 → T003 → T004 → T005. T006–T009 обеспечивают T010; T007 до T008/T009. T011/T012 до T013. T014 до T015/T016. T003–T013 до интеграционных T015–T018. Все implementation задачи до T019/T020/T021. Каждая история проверяется своими сценариями, общие инварианты должны сохраняться после каждого шага. Одновременная запись в общие файлы не разрешена; [P] не назначен.

## Проверки историй

US1: S01–S06; US2: S17,S21,S22,S30,S38; US3: S07–S16,S36; US4: S18–S23,S41,S44,S46,S49; US5: S24–S29,S31–S35,S37–S40,S42,S43,S45,S47,S48,S50,S51.

Tasks открыты до подтверждённой реализации. T021 не закрывается локальным тестом или опубликованным артефактом без установленной версии. Commit/push/release не выполняются без применимого разрешения.

## Phase 1: Convergence

- [X] T022 [HIGH] Проверить installed GRAF Dev: остановку managed player, VoiceOver/keyboard, 100 операций, SC-002/003/006/007 и полную S01–S51; записать измерения и непроверенные ограничения в specs/262-recording-deletion-lifecycle/evidence.md per FR-012/015/017, SC-001–007 (partial). — issue #6902; PR #6911.
- [X] T023 [HIGH] Проверить upgrade/rollback на синтетическом v2 queue и существующей БД: legacy ownership recovery, preflight дублированных purge tasks, старый/новый bridge/server, сохранение tombstones при restore; записать в specs/262-recording-deletion-lifecycle/evidence.md per FR-014/019/020/022, plan: миграция и выпуск (partial). — issue #6903; PR #6911.


T001–T023 отмечены по проверенному коду, матрице сценариев, независимому обзору и установленной приёмке из evidence.md. T021: governance-fast/pr-metadata и GRAF Dev 13/13 на 0e19; окончательный коммит документов получает собственные CI и installed receipts, записываемые в PR. Отметки не означают 51 отдельный сквозной GUI-запуск или публичный выпуск. GitHub issues остаются открыты до слияния PR и live closeout по docs/agent-guidance/tracker-policy.md; release-full и публичная поставка относятся к отдельному замороженному кандидату.
