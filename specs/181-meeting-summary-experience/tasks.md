# Tasks: Полезные итоги встреч

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [quickstart.md](quickstart.md), [contracts/](contracts/)

## Phase 1: User Story 1 — Сразу получить полезный результат (P1)

**Goal**: новая встреча показывает первый строго проверенный AI-результат или честное pending/error state, но никогда не публикует extractive mock.

**Independent test**: revision-scoped import with no current outcome cannot expose deterministic content; a valid automatic AI result is published to the type slot only after trusted provider validation.

- [x] T001 [US1] Add RED lifecycle coverage for non-published deterministic extraction and first-AI trusted publication in `apps/server/tests/integration/test_meeting_outcomes_generation.py`
- [x] T002 [P] [US1] Add accepted/rendering regressions for no-result pending, blocked, empty and AI-ready states in `apps/server/tests/integration/test_cabinet_meeting_outcomes.py`
- [x] T003 [US1] Stop publishing revision-scoped deterministic extraction as ready or accepted outcomes in `apps/server/src/twobrain_rec_server/outcomes/service.py`
- [x] T004 [US1] Publish every generated result, including `automatic_baseline`, only through the trusted provider-call and type-slot boundary in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [x] T005 [US1] Preserve dispatch, source, deletion, expected-current and idempotency fences for automatic publication in `apps/server/tests/integration/test_outcome_generation_dispatch.py`
- [x] T006 [US1] Render one honest meeting-level preparing/empty/error result instead of heuristic content or eight duplicate empty categories in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

## Phase 2: User Story 2 — Безопасно выбрать формат и обновить итоги (P1)

**Goal**: пользователь понимает side effect выбора, видит ход обновления, а проверенная новая версия автоматически заменяет текущую только в своём type slot.

**Independent test**: select/refresh creates one technical attempt, current result remains stable while it runs, recovery is visible, and successful publication changes only the target slot atomically.

- [x] T007 [P] [US2] Define RED UI contract assertions for format purpose/current marker, named generation region, separate live text/actions and automatic replacement semantics in `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [x] T008 [P] [US2] Add API lifecycle regressions for duplicate intent, history unavailable, preview unavailable, stale, expired and accepted-pointer conflict in `apps/server/tests/unit/test_summary_candidate_revisions.py`
- [x] T009 [US2] Clarify format side effects, current selection and full-catalog purpose copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [x] T010 [US2] Separate passive generation status from actions and make the current-result transition a named region in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [x] T011 [US2] Implement automatic screen refresh after trusted publication, visible generation-history recovery, retry and neutral slow state in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [x] T012 [US2] Add current/pending/review/slow/attention styles and responsive comparison layout without new visual dependencies in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

## Phase 3: User Story 3 — Получить результат под тип встречи (P1)

**Goal**: девять форматов дают заметно разные, grounded and useful outputs rather than one generic prompt with renamed heading.

**Independent test**: every format carries unique priorities/exclusions, passes strict schema/source constraints on suitable fixtures and does not invent format-specific facts on unsuitable fixtures.

- [x] T013 [P] [US3] Add per-format prompt contract and injection/owner/decision/action regression cases in `apps/server/tests/unit/test_outcome_prompts.py`
- [x] T014 [P] [US3] Add catalog purpose/section/version compatibility assertions for all nine built-ins in `apps/server/tests/unit/test_summary_templates.py`
- [x] T015 [US3] Replace one-line format focus strings with explicit format-specific goal, priority, exclusion and rendering guidance in `apps/server/src/twobrain_rec_server/cli/langfuse_prompts.py`
- [x] T016 [US3] Improve concise user-facing purposes while preserving built-in keys and version compatibility in `apps/server/src/twobrain_rec_server/outcomes/templates.py`
- [x] T017 [US3] Extend synthetic prompt-evaluation fixtures for suitable, unsuitable, corrected, cancelled, unknown-owner/date, multilingual and injection meetings in `apps/server/tests/unit/test_outcome_prompts.py`
- [ ] T018 [US3] Run local/private outcome generation for all nine formats and record metadata-only aggregate rubric results in `specs/181-meeting-summary-experience/validation/format-evaluation.md`

## Phase 4: User Story 4 — Проверить источник и вернуться к результату (P2)

**Goal**: source evidence remains exact but secondary; navigation and return work in current results and in-flight generation without losing player or generation state.

**Independent test**: keyboard user opens an exact source, keeps playback/generation state and returns to the same current/in-flight context in browser and embedded routes.

- [x] T019 [P] [US4] Add source-jump/return, tab-state, player-state and candidate-review focus regressions in `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [x] T020 [US4] Preserve accepted/candidate review context and expose a return-to-review action around source navigation in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

## Phase 5: User Story 5 — Управлять личными форматами без риска (P2)

**Goal**: owner can create, edit, delete and choose a personal default while historical result/template snapshots remain immutable.

**Independent test**: personal default is authorized only for the same active workspace/owner, drives future automatic generation, and edit/delete does not alter existing outcomes.

- [x] T021 [P] [US5] Replace the legacy personal-default prohibition with positive authorization and history-preservation contract tests in `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [x] T022 [US5] Allow an active personal template to become workspace default with existing owner/RLS/CSRF gates in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [x] T023 [US5] Resolve automatic candidates from either built-in or active personal default snapshots in `apps/server/src/twobrain_rec_server/outcomes/ai_service.py`
- [x] T024 [US5] Show personal-default state and bounded load failures in summary settings UI in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

## Phase 6: User Story 6 — Keyboard, focus, zoom and responsive parity (P2)

**Goal**: complete summary workflow remains understandable and operable with keyboard/assistive technology in browser and embedded macOS at 200% zoom.

**Independent test**: keyboard-only selection, generation, source return and automatic refresh preserve focus and content at desktop/mobile widths and 200% embedded zoom.

- [x] T025 [P] [US6] Add keyboard, live-region, dialog/listbox focus-return and 200% reflow contract regressions in `apps/server/tests/contract/test_summary_template_ui_contract.py`
- [x] T026 [US6] Keep candidate live text bounded, review focus predictable and narrow/zoom actions reachable in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [x] T027 [US6] Raise embedded workspace zoom support from 140% to the 200% accessibility target in `apps/macos/RecApp/Sources/Cabinet/WorkspaceZoom.swift`
- [x] T028 [US6] Add 200% zoom boundary and persisted-value regressions in `apps/macos/Shared/Tests/WorkspaceZoomTests.swift`

## Phase 7: Cross-cutting validation and closeout

- [x] T029 [P] Run focused PostgreSQL suite from `specs/181-meeting-summary-experience/quickstart.md` and record metadata-only results in `specs/181-meeting-summary-experience/validation/focused.md`
- [x] T030 [P] Run synthetic browser and embedded-route matrix for all formats, buttons, recovery, keyboard, 390px and 200% zoom and record metadata-only results in `specs/181-meeting-summary-experience/validation/ui-matrix.md`
- [ ] T031 Run version-bound local/private quality and latency evaluation, including all nine formats and aggregate user-usefulness gaps, in `specs/181-meeting-summary-experience/validation/format-evaluation.md`
- [x] T032 Run `infra/scripts/ci-local.sh --fast` and record the exact result in `specs/181-meeting-summary-experience/validation/closeout.md`
- [x] T033 Update `[Unreleased]` behavior, UX and validation notes in `CHANGELOG.md`
- [x] T034 Run `@ponytail-review` over the final diff and remove unnecessary abstractions or dependencies before PR handoff
- [x] T035 Reconcile every completed task with its GitHub issue and leave commit, PR, Langfuse promotion, release and deploy pending explicit approval in `specs/181-meeting-summary-experience/validation/closeout.md`

## Dependencies

- US1 is the root correctness slice and blocks a truthful end-to-end claim.
- US2 and US3 can proceed after US1 lifecycle semantics are fixed.
- US4 and US6 depend on the US2 review state.
- US5 is independently implementable after existing template contracts are understood.
- Cross-cutting validation depends on every implemented story.

## Parallel opportunities

- T002 can run beside T001; T013 and T014 can run in parallel; T019 and T021 can run in parallel after their prerequisite story state is stable.
- T029 and T030 can run in parallel once implementation is complete.

## Implementation strategy

1. Ship the smallest trusted vertical slice first: US1.
2. Clarify automatic trusted replacement without changing slot history: US2.
3. Strengthen prompts in the existing one-call architecture: US3.
4. Close source, personal-format and accessibility parity: US4–US6.
5. Validate locally; do not commit, promote, release or deploy without the separate approval gate.
