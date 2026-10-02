# Tasks: Непрерывная запись и доступ к аудио
Input: spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md.

## Phase 1: Foundation
- [X] T001 Согласовать требования и независимый анализ ворот в specs/284-recording-continuity-playback/checklists/ и analysis.md; синхронизировать задачи с GitHub.

## Phase 2: US1 (P1)
Independent validation: one simulated45min recording, no repeat prompt; end15s, unknown600s; target controls unchanged.
- [X] T002 [US1] Добавить регрессионные проверки снимков, дочерних процессов и длительного звонка в apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift и MeetingDetectionRecordingLifecycleTests.swift (исполняемый600s predicate/детектор, отсутствие влияния старого журнала, exact bundleID); подтвердить отказ до исправления.
- [X] T003 [US1] Исправить подтверждение текущей активности и согласование без сбросов в apps/macos/RecApp/Sources/MeetingDetection/ и apps/macos/RecApp/App/TwoBrainRecApp.swift.

## Phase 3: US2 (P1)
Independent validation: local playback only own matched meeting, correct quota message; blocked/deleted/cross-route cases rejected.
- [X] T004 [US2] Добавить регрессионные проверки квоты и локального открытия в apps/server/tests/contract/test_playback_status_contract.py, apps/server/tests/browser/local-recording-detail.test.cjs и apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift; подтвердить отказ до исправления.
- [X] T005 [US2] Открывать сохранённую локальную копию из карточки с проверкой маршрута в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift и apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js; исправить сообщение/действие квоты в cabinet/view_models.py и templates/.

## Phase 4: Validation
- [X] T006 Выполнить high-risk-product проверки, сходимость и добавить changes/unreleased/F284.yaml; записать доказательства и оставшиеся аппаратные/CI/релизные ворота в specs/284-recording-continuity-playback/validation.md.

## Dependencies & Execution Order
T001→T002→T003; T001→T004→T005; T003+T005→T006. Tests precede implementation. No parallel file ownership assigned. No implementation commit without explicit user approval after validation. Publication is authorized on 2026-10-02 and remains subject to the separate release gates.

## Phase 5: Convergence
- [X] T007 [US2] Исправить привязку локального аудио к соседнему блоку проигрывателя и сохранять/отзывать кнопку после прямого опроса в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js; проверить настоящую структуру страницы, смену состояния и access_denied в apps/server/tests/browser/local-recording-detail.test.cjs.
- [X] T008 [US1] Сохранить незавершённое предложение записи при техническом перезапуске наблюдения в apps/macos/RecApp/App/TwoBrainRecApp.swift; проверить работоспособность исходного окна без повторного предложения в apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift.
- [X] T009 [US2] Отбросить запоздалый отказ доступа предыдущей карточки после асинхронного чтения ошибки в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js; проверить переход на другую встречу с отложенным 403 в apps/server/tests/browser/local-recording-detail.test.cjs.
