# Tasks: Детальный metadata-only отчёт поддержки

**Input**: Design documents from `/specs/114-support-incident-diagnostics/`
**Prerequisites**: `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

## Phase 1: Setup

- [X] T001 [P] Обновить managed plan reference для feature 114 и подготовить bounded v2 fixtures в `AGENTS.md` и `apps/macos/Shared/Tests/DesktopSupportIncidentFixtures.swift`
- [X] T002 [P] Добавить v1/v2 safe payload helpers и запрещённые-field assertions в `apps/server/tests/unit/test_support_incident_redaction.py`

## Phase 2: Foundational contract and privacy guardrails

**Purpose**: Сначала закрепить общий контракт и негативные privacy проверки, от которых зависят все user stories.

- [X] T003 [P] [US2] Добавить regression tests для v2 field allowlist, bounded timeline/retry и неизвестных/unsafe полей в `apps/server/tests/unit/test_support_incident_redaction.py`
- [X] T004 [P] [US2] Добавить Swift tests для v2 schema, client correlation, canonical stage и запрета raw path/token/content в `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T005 Реализовать v1/v2 schema compatibility, allowlist/validators и redaction для timeline/retry/correlation fields в `apps/server/src/twobrain_rec_server/support/redaction.py`
- [X] T006 [P] Реализовать bounded metadata models для timeline/retry, v2 report encoding и существующих runtime fields (version/platform/locale/timezone) в `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`

## Phase 3: User Story 1 — Понятный private Issue (P1)

**Goal**: Поддержка видит stage, problem, state matrix, correlation и безопасную историю без ручного разбора raw logs.

**Independent Test**: `tests/unit/test_support_incident_github_issue_body.py` и contract fixture создают v2 report и находят stage/problem/CUST/fingerprint/retry/timeline в private Issue body без запрещённых значений.

- [X] T007 [P] [US1] Добавить тесты title/labels `[114][P*][support/custody] T000`, state matrix, timeline/retry и сохранения human sections при dedupe update в `apps/server/tests/unit/test_support_incident_github_issue_body.py`
- [X] T008 [P] [US1] Добавить contract/integration проверки private repository, feature/stage/problem search metadata и одного Issue на повторный dedupe в `apps/server/tests/contract/test_support_incident_contract.py` и `apps/server/tests/integration/test_support_incidents.py`
- [X] T009 [US1] Обновить генератор private Issue: feature 114 labels, runtime `T000`, русская state matrix, correlation summary, bounded timeline/retry и full redacted JSON в `apps/server/src/twobrain_rec_server/support/github_issues.py`
- [X] T010 [US1] Обновить support incident sync/update path так, чтобы latest v2 report и server redaction metadata попадали в тот же deduped Issue без raw fields в `apps/server/src/twobrain_rec_server/support/incidents.py`

## Phase 4: User Story 2 — Правдивая локальная и серверная истина (P1)

**Goal**: Устаревшие `uploaded/finalized` флаги не маскируют удаление, access block или неизвестный server state.

**Independent Test**: Swift fixtures для server deletion, access block, processing failure, no sync response и successful finalize дают ожидаемые canonical stage, copy state, risk, reason и next action.

- [X] T011 [P] [US2] Добавить тесты decoding всех safe sync-state fields и сохранения server deletion/access/review/processing reason в `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T012 [P] [US2] Добавить regression tests для problem-code precedence, server copy state/data-loss risk и `pending` purge task в `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T013 [US2] Расширить `ServerTruthFingerprint` safe deletion/access/upload/processing/review/conflict fields и их merge/serialization compatibility в `apps/macos/Shared/Sources/Models/AudioModelCore.swift`
- [X] T014 [US2] Декодировать существующий sync-state contract и сохранить bounded safe server truth/conflict fields в `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T015 [US2] Исправить projection/report truth precedence: canonical stage, server/local copy state, problem code, risk, local purge enum, timeline и retry history в `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [X] T016 [US2] Обновить server redaction validators/contract fixtures для safe server truth fields, v1 missing fields и deletion/access scenarios в `apps/server/src/twobrain_rec_server/support/redaction.py` и `apps/server/tests/unit/test_support_incident_redaction.py`

## Phase 5: User Story 3 — Единый подробный clipboard fallback (P1)

**Goal**: При недоступном сервере пользователь копирует тот же bounded redacted report, а локальная запись сохраняется.

**Independent Test**: submission failure + copy flow yields the same report fingerprint/schema/stage/problem as submit path and contains no banned data.

- [X] T017 [P] [US3] Добавить queue/action-strip tests для detailed clipboard report, local fingerprint без CUST и clipboard failure preservation в `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` и `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T018 [US3] Добавить read-only queue API, который строит тот же v2 report для submission и clipboard, с bounded text/JSON fallback в `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T019 [US3] Передать copy callback через `DesktopSupportIncidentActionStrip`/`DesktopMeetingShellView` и писать в NSPasteboard только полученный metadata-only text в `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`, `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift` и `apps/macos/RecApp/App/TwoBrainRecApp.swift`

## Phase 6: User Story 4 — Поиск и идемпотентность (P2)

**Goal**: Повторные отправки одной записи обновляют один Issue, а разные stages/problems фильтруются по canon metadata.

**Independent Test**: synthetic reports with distinct fingerprints/stages/problems create/update predictable private Issues and preserve affected count bounds.

- [X] T020 [P] [US4] Добавить тесты server/client dedupe key с recording fingerprint, issue search labels и affected identity bounds в `apps/server/tests/unit/test_support_incident_redaction.py`, `apps/server/tests/unit/test_support_incident_github_issue_body.py` и `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [X] T021 [US4] Сделать client/server dedupe correlation устойчивой к повторной отправке одной записи и различающей независимые записи в `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift` и `apps/server/src/twobrain_rec_server/support/redaction.py`
- [X] T022 [US4] Проверить idempotency/update path и bounded affected merge без создания duplicate Issue в `apps/server/src/twobrain_rec_server/support/incidents.py` и `apps/server/tests/integration/test_support_incidents.py`

## Phase 7: Polish and cross-cutting validation

- [X] T023 [P] Обновить русскую `[Unreleased]` запись о v2 report, truthful server state и clipboard fallback в `CHANGELOG.md`
- [X] T024 [P] Обновить fixture/contract documentation links и evidence wording без raw paths/content в `specs/114-support-incident-diagnostics/quickstart.md` и `docs/current-product-status.md`
- [X] T025 Запустить quickstart focused tests, negative metadata scan и исправить найденные регрессии по `specs/114-support-incident-diagnostics/quickstart.md`
- [X] T026 Запустить repository gate `infra/scripts/ci-local.sh`, проверить `git diff --check`, no-secret scan и зафиксировать evidence перед PR

## Dependencies

```text
T001-T006 -> T007-T010 (Issue)
T001-T006 -> T011-T016 (truth)
T006,T015 -> T017-T019 (fallback)
T005,T009,T015 -> T020-T022 (dedupe/search)
T007-T022 -> T023-T026 (polish/closeout)
```

User story completion order: **US2 foundational truth** and **US1 Issue** can
start in parallel after T001-T006; **US3** depends on v2 report builder;
**US4** depends on server/client correlation; polish depends on all story
validation.

## Parallel execution examples

```text
# After foundational contract work:
T007 (Issue body tests) || T011 (sync decoder tests) || T017 (fallback tests)

# After their tests are written:
T009 (Issue builder) || T013 (ServerTruthFingerprint) || T018 (queue report API)

# Final checks are sequential because they share the resulting worktree:
T025 -> T026
```

## Implementation strategy

1. Establish privacy/schema guardrails and tests first.
2. Fix server truth precedence and report v2 before changing UX fallback.
3. Make Issue generation and clipboard consume the same report construction.
4. Validate dedupe/search and run the full local gate.
5. Keep code uncommitted until explicit user approval after validation; deploy is
   outside this feature turn.
