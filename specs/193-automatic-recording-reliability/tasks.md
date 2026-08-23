# Tasks: Надёжность автоматической записи

**Input**: Design documents from `/specs/193-automatic-recording-reliability/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/automatic-recording-runtime.md`, `quickstart.md`

**Tests**: Обязательны до реализации из-за high-risk capture/auth lane.

## Phase 1: Source truth and candidate lifecycle

**Goal**: Порядок независимых platform events больше не меняет результат встречи.

**Independent Test**: Все перестановки AudioHAL/Sensor Indicator start/end дают
один trigger, не завершаются при одном active source и дают один end после grace.

- [X] T001 [P] [US2] Добавить failing parser/log conversion tests для точного `audioHAL`/`sensorIndicator` source и duplicate diffs в `apps/macos/Shared/Tests/MacOSAudioOwnershipParserTests.swift` и `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T002 [P] [US2] Добавить failing detector tests для перестановок двух sources, all-source end, grace cancellation, reset и новой встречи того же bundle в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T003 [US2] Добавить source к ownership event и хранить per-bundle active source set с all-source end/reset semantics в `apps/macos/Shared/Sources/MeetingDetection/MacOSAudioOwnershipParser.swift`, `apps/macos/RecApp/Sources/MeetingDetection/MacOSAudioOwnershipLogStream.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`

**Checkpoint**: candidate lifecycle детерминирован по источникам и допускает новую
встречу после реального end/reset.

---

## Phase 2: User Story 1 — truthful gate and accepted delivery (Priority: P1)

**Goal**: Countdown обещается только при current authorization, а временный
consumer blocker не поглощает trigger.

**Independent Test**: Missing/stale policy блокирует до prompt; retryable rejection
переоценивается ≤2 s; accepted/Skip/manual Stop не повторяется до end.

- [X] T004 [P] [US1] Добавить failing detector tests для offer/accepted/retryable/terminal outcomes, 2-second retry throttle и suppression deduplication в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T005 [US1] Заменить emission-based закрытие candidate на явный consumer outcome и bounded retry в `apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift`
- [X] T006 [P] [US1] Добавить failing app-policy tests для запрета prompt countdown без current policy/ack и повторной проверки button/timeout/saved-target start в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` и `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift`
- [X] T007 [US1] Провести prompt, timeout и saved-target через единый current policy/ack/readiness gate и возвращать detector-у consumer outcome в `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: UI больше не обещает запрещённый старт; временный blocker может
восстановиться без закрытия встречи, terminal action не создаёт дубль.

---

## Phase 3: User Story 2 — observer startup, recovery and wake (Priority: P1)

**Goal**: Один observer восстанавливает current state после startup, сбоя и wake.

**Independent Test**: Controlled child finish не создаёт parallel process;
unexpected finish/wake дают snapshot+live generation ≤5 s; deliberate stop не
перезапускается.

- [X] T008 [P] [US2] Добавить failing observer tests для bounded atomic snapshot, timeout fallback, unexpected completion retry, single child и deliberate stop в `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift`
- [X] T009 [US2] Реализовать один bounded snapshot/live supervisor с atomic final-state reconciliation, 1-second retry и точным child cancellation в `apps/macos/RecApp/Sources/MeetingDetection/MacOSAudioOwnershipLogStream.swift`
- [X] T010 [US2] Подключить startup/restart/wake reconciliation, detector reset и чистое task ownership в `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: startup во время активной synthetic встречи и observer recovery
проходят обычные debounce/allowlist/policy gates без второго stream.

---

## Phase 4: User Story 3 — authoritative web/native auth (Priority: P1)

**Goal**: Native registry использует актуальную same-origin web session и не
продолжает скрытно отправлять logout/replaced cookie.

**Independent Test**: Login/replacement/logout/re-login fixtures оставляют ровно
current applicable cookie; выбор одинаков при любом порядке storage.

- [X] T011 [P] [US3] Добавить failing tests для expiry, secure, domain/path applicability, deterministic selection, stale replacement и logout removal в `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T012 [US3] Реализовать deterministic applicable-cookie selection в `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T013 [US3] Сделать WebKit cookie snapshot авторитетным для настроенного same-origin auth scope и удалять stale/logout copies в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift`

**Checkpoint**: после reconciliation прежний session value не может попасть в
native registry request, а fail-closed behavior сохраняется при отсутствии auth.

---

## Phase 5: User Story 4 — diagnostics and full validation (Priority: P2)

**Goal**: Полный путь восстанавливается по metadata-only evidence и защищён всеми
repository gates.

**Independent Test**: Synthetic positive/negative flows имеют source, candidate,
consumer, observer и start/stop outcomes без запрещённого содержимого.

- [X] T014 [US4] Добавить bounded metadata-only source/decision/consumer/observer/start-stop diagnostics через существующий logger в `apps/macos/RecApp/App/TwoBrainRecApp.swift` и `apps/macos/RecApp/Sources/MeetingDetection/MacOSAudioOwnershipLogStream.swift`
- [X] T015 [P] [US4] Обновить русский changelog и текущий продуктовый статус без обещания production enablement в `CHANGELOG.md` и `docs/current-product-status.md`
- [X] T016 [US4] Выполнить focused suites, `infra/scripts/ci-local.sh --fast`, `infra/scripts/ci-local.sh --full`, отдельную dev-сборку и child-recovery smoke; записать metadata-only evidence в `specs/193-automatic-recording-reliability/validation/implementation-evidence.md`

## Dependencies & Execution Order

- T001–T002 фиксируют source contract до T003.
- T004 выполняется до T005; T006 — до T007; T007 зависит от T005.
- T008 выполняется до T009; T010 зависит от T003 и T009.
- T011 выполняется до T012–T013.
- T014 зависит от T007, T010 и T013; T015 может выполняться после behavior freeze.
- T016 выполняется последней после всех implementation tasks.

## Parallel Opportunities

- T001 и T002 затрагивают независимые test sections, но при последовательной
  локальной работе объединяются в один TDD red pass.
- T006, T008 и T011 независимы после source model foundation.
- T015 не блокирует focused implementation tests.

## Implementation Strategy

1. Сначала source identity и один candidate state machine.
2. Затем consumer acknowledgement и truthful authorization gate.
3. Затем один supervised snapshot/live observer.
4. Затем same-origin cookie reconciliation.
5. В конце metadata-only evidence, dev runtime smoke и полные gates.

Не добавлять dependency, endpoint, database, audio engine или global cookie
cleanup. Production policy, deployment, release и installed app не менять.
