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

- [X] T010 [US1] Изолировать недоступные процессы в текущем снимке CoreAudio, передавать подтверждённую активность без ложного окончания по неполному снимку; добавить исполняемые проверки смешанного снимка, точного bundleID и45min непрерывности в apps/macos/RecApp/Sources/MeetingDetection/, apps/macos/RecApp/App/TwoBrainRecApp.swift и apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift.

## Phase 6: Аппаратная сходимость
- [X] T011 [US1] Воспроизвести source_overflow контрольного Telemost в исполняемой проверке writer с разными размерами пакетов; исправить доказанный порядок обработки накопленных источников и добавить безопасные относительные счётчики переполнения в apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift и RecordingAudioTimeline.swift, RecordingSampleSources.swift, MicrophoneCaptureService.swift и PrivacySuppressingSampleSource.swift; отдельно маршрутизировать обычную диагностику в apps/macos/RecApp/App/TwoBrainRecApp.swift; сохранить отрицательные overflow/gap/format/stop проверки в apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift; повторить разрешённый45min физический звонок и доступ к обоим файлам.

T011 принята после физического контроля45min40s на продуктовой версии6f1b44175181 и независимой проверки доказательств: hardware-acceptance.json и validation.md. Прежний detector-only45min не заменяет эту приёмку. Слияние требует текущих CI финального документационного SHA; выпуск сохраняет отдельные release-full/Apple/публичные и установленные ворота.

## Phase 7: Закрытие замечаний PR
- [ ] T012 [US1] Сохранять заглушение всех ожидающих микрофонных кадров через быстрый resume до drain в apps/macos/RecApp/Sources/Capture/PrivacySuppressingSampleSource.swift и существующих источниках/тестах; red/green очереди и интеграционного writer, независимое ревью и актуальная Dev-приёмка.
- [X] T013 [US2] Связать все ответы playback poll с meetingId до запроса и отбросить устаревшие recovery/body/error в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js; исполняемый red и браузерные проверки повторно используемого main в local-recording-detail.test.cjs и сохранить полный контракт действующего отзыва доступа в apps/server/tests/contract/test_cabinet_static_assets_contract.py.

T012 и T013 блокируют слияние. Независимые файлы могут проверяться параллельно после reviewer-owned checklist/analyze/issue-sync PASS.

## Phase 8: Граница производителя
- [ ] T014 [US1] Устранить гонку добавления микрофонных кадров между снимком FIFO и resume в apps/macos/RecApp/Sources/Capture/PrivacySuppressingSampleSource.swift, RecordingSampleSources.swift и MicrophoneCaptureService.swift; детерминированный red/green, атомарный producer/read boundary, forwarding, сохранённые приватность/checkpoint/пределы в apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift; независимое ревью, текущие Dev/CI/release gates.

T014 — новое замечание PR4171728042 на e4b1ebb774d661348098bc89fbff398a8ea0a165. Блокирует слияние; не закрывается прежним T012 снимком,80/0 или45min приёмкой.

## Phase 9: Завершение без реестра
- [ ] T015 [US1] Сохранять15s ended при nil registry в MacOSMeetingActivityDetector и TwoBrainRecApp; исполняемые полное/неполное отсутствие,14.999/15s, повторная активность, отсутствие новых предложений/телеметрии и восстановление реестра; production wiring, независимое ревью, актуальные Dev/CI.
