# Quickstart: Essential Interface Polish Validation

Run from the repository root unless a step says otherwise. Use synthetic or redacted meeting data only. Do not commit runtime screenshots containing real meeting metadata.

## 1. Preconditions

```sh
git branch --show-current
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
git status --short
```

Expected:

- branch is `104-essential-interface-polish`;
- feature paths point to `specs/104-essential-interface-polish`;
- unrelated user changes are identified and preserved.

## 2. Approved Pre-build Visual Target

Use [visual-target.md](./visual-target.md) as the visual implementation source.
The selected Stitch source is project `8185028688921991455`, screen
`e3c3421bd78e4320845d072c6a7193cc`; local HTML/screenshots stay outside git.

Pre-build evidence already established:

- synthetic target rendered at `1280×760` and `1040×680`;
- all title/duration/status/date columns, upload, and the native capture rail
  remain visible at the minimum size;
- the minimum-width accessibility tree retains exact names for `Поиск встреч`,
  `Фильтры`, `Сортировка`, `Загрузить запись`, `Готово к записи`,
  `Начать запись`, and `Открыть управление записью`;
- the ordinary tree contains zero checkbox/delete nodes; hover and eight-step
  keyboard traversal to the first row reveal its exact selection/delete names,
  followed by the separate `Открыть встречу …` result link;
- the app shell fills both target viewports without an outer centered frame;
- the rendered target uses a 20 px heading, 36 px toolbar controls, 48 px rows,
  one-line `Обрабатывается`, lowercase Russian month abbreviations, and a
  non-color-only readiness check;
- Playwright measures 32×32 CSS px for contextual row hit areas, 40×40 CSS px
  for native-rail disclosure, and reports `animation: none` plus effectively
  immediate transitions under `prefers-reduced-motion: reduce`;
- the target contains no plan/trial label, calendar card, disabled destination,
  duplicate search, idle diagnostic, or private content;
- the design-time HTML is evidence only and MUST NOT introduce its CDN/runtime
  dependencies into production.

## 2A. Clean Pre-implementation Analyze Evidence

The third read-only `$speckit-analyze` pass completed on 2026-07-13 after all
visual-contract remediation:

- requirements: `35` functional + `12` success criteria, `47/47` mapped;
- implementation tasks: `T001–T037`, sequential with no duplicate or missing ID;
- exact task paths: `32/32` exist;
- state evidence: `16/16` classes match between the visual target and this guide;
- UX requirement-quality checks: `61/61` passed;
- critical/major/minor findings, constitution conflicts, active ambiguities,
  stale screen IDs, broken relative links, and unmapped requirements: `0`.

This evidence validates the specification package for task/issue sync and
implementation; it does not claim production code or runtime states are already
implemented.

## 2B. Implementation Baseline

Baseline captured on 2026-07-13 before any feature-104 product-code change:

- server command: the exact focused command in section 3;
- server result: `74 passed`, `0 failed`, `1 warning` in `25.95s`;
- server warning: the environment's existing Starlette deprecation warning for
  the `httpx` compatibility import in `fastapi.testclient`; no product-test
  failure accompanied it;
- macOS command: the exact focused command in section 4;
- macOS result: `58 tests`, `0 failures`, build and selected suites successful;
- known pre-existing product-test failures in this baseline: `0`;
- unrelated worktree changes preserved and excluded from feature evidence:
  `.specify/templates/checklist-template.md`,
  `.specify/templates/plan-template.md`, `AGENTS.md`, and
  `docs/agent-guidance/ponytail-upstream.md`.

The selected Stitch project `8185028688921991455` and screen
`e3c3421bd78e4320845d072c6a7193cc` were rechecked at `1280×760` and
`1040×680`. Synthetic design-time before/target artifacts remain outside git
under the local Codex visualization workspace. Only the viewport and state
identifiers are recorded here; no private meeting metadata is included.

## 3. Focused Server Tests

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_navigation_model.py \
  tests/unit/test_cabinet_template_sections.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_hx_fragments.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_cabinet_static_assets_contract.py
```

Expected:

- only enabled navigation is rendered;
- no unsupported trial/plan or empty calendar projection is rendered;
- one search field, contextual filter/sort, and no disabled placeholder controls;
- selection/delete semantics and HTMX fragment replacement still pass;
- human title/status/progress presentation passes;
- no secret/private-content egress regression.

## 4. Focused macOS Tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'AppControlAccessibilityTests|CaptureControlTests|DesktopCabinetConfigurationTests|DesktopCabinetWorkspaceTests|DesktopMeetingShellWebViewBoundaryTests'
```

Expected:

- compact rail Start/Stop and inspector semantics pass;
- active recording does not force workspace-width change;
- titlebar HUD keeps one-action Stop;
- idle UI omits telemetry/report/diagnostics/meters;
- actionable recovery remains truthful and accessible.

### US1 implementation evidence

Tests-first proof on 2026-07-13:

- the first US1 run failed in exactly seven intended places: disabled navigation,
  invite/trial sidebar copy, unconditional calendar presentation, duplicated
  first-run actions, and missing contextual filter/reset semantics;
- after the scoped implementation, the complete US1 set passed: `58 passed`,
  `0 failed`, with the same environment-owned Starlette deprecation warning;
- the rendered information order exposes `Мои встречи`, one `Поиск встреч`,
  `Фильтры`, current `Сортировка`, `Загрузить`, then `Записи встреч` and the
  result links; this is the five-second comprehension path;
- only `Мои встречи`, `Настройки`, and `Выйти` remain in the primary sidebar;
- filter reset is absent in the default state and appears once when search or a
  filter is active;
- bulk delete controls remain hidden until a row is selected; the removed
  saved/download placeholders have no replacement request or background work;
- the no-meetings state points to the existing toolbar upload and the separate
  native recording surface without an app-download, onboarding, or calendar
  duplicate.

## 5. Release Build

```sh
swift build --package-path apps/macos -c release --product TwoBrainRecApp
```

Expected: build exits `0` with no missing symbol or generic-view composition error.

## 6. Static Presentation Audit

Search the ordinary user-facing templates and native views:

```sh
rg -n "Телеметрия кандидатов|Реестр .*источник|Apple voice processing|WebRTC|Скопировать отчет|Отправить отчет|Диагностика|Скачивание появится позже" \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/macos/RecApp/Sources/Cabinet \
  apps/macos/RecApp/Sources/Capture
```

Expected: no ordinary main-window rendering of these phrases. Matches are allowed only in internal diagnostics, support implementation, tests that assert absence, or deliberately scoped settings/support surfaces.

Also confirm unsupported account/calendar presentation is absent from the main
window:

```sh
rg -n "Пробный период 7 дней|Ближайшие встречи появятся|Подключить календари" \
  apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html \
  apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html
```

Expected: no matches. The real calendar configuration route remains reachable
through the working `Настройки` destination.

Also confirm no disabled roadmap surface remains:

```sh
rg -n "Пригласить|Общие|Действия|Активность|Сохраненные" \
  apps/server/src/twobrain_rec_server/cabinet/templates/cabinet \
  apps/server/src/twobrain_rec_server/cabinet/view_models.py
```

Expected: no main-sidebar/list placeholder rendering. Detail-page domain copy such as real action items may remain.

## 7. Live Main-window Matrix

Build/run through the repository’s normal local app workflow, then inspect the main window at:

- `1040×680` minimum;
- `1280×760` default;
- one wider window, approximately `1440×900` or the available display maximum.

Exercise all state classes from the visual contract:

1. session/sign-in required;
2. permission required;
3. idle/ready;
4. detected meeting prompt;
5. active recording;
6. paused recording;
7. stopping/finalizing;
8. locally saved copy;
9. active upload;
10. processing;
11. ready/ready-with-notes result;
12. no meetings;
13. selected rows;
14. searched/filtered/sorted list and no-result refinement;
15. cabinet offline/unavailable;
16. actionable degraded failure.

The row fixtures additionally include a long Russian title, a generated capture
title with trustworthy time, a generated capture title without trustworthy
time, a generated manual-upload ID, and a file-like title.

For every size, verify:

- no horizontal scroll, overlap, or clipped critical action;
- sidebar, meeting workspace, and 52 pt capture rail retain stable ownership;
- wordmark is compact and only enabled destinations are visible;
- no hard-coded plan/trial label or unsupported calendar/upcoming block appears;
- search is unique; filter/sort show active state and reset;
- reading mode does not look like bulk administration;
- completed rows have no 100% meter;
- generated titles and durations are human/Russian;
- selected state is subtle but clear;
- Start is direct from the compact native surface;
- recording start does not expand the panel or move keyboard focus;
- active recording always shows a native indicator and one-action Stop;
- idle state has no meters, telemetry, report buttons, trust card, or diagnostics disclosure.

## 8. Interaction And Accessibility Matrix

With mouse/trackpad, keyboard only, and the macOS accessibility tree:

1. Search and clear search.
2. Open filters, choose status/access, observe active count, reset.
3. Change sorting and confirm the current choice is announced.
4. Focus a row, reveal selection, select multiple rows, clear selection.
5. Open and cancel per-row and bulk delete; confirm focus recovery.
6. Open and close the native inspector.
7. Start a short synthetic recording, Pause, Resume, and Stop.
8. Exercise the detected-meeting prompt, a permission blocker, and an actionable local-custody failure.
9. Make the cabinet unavailable and confirm local native authority remains truthful.

Expected:

- all interactive elements have Russian names matching visible labels;
- focus is visible and not obscured;
- disclosures expose expanded/collapsed state;
- hover-only elements also reveal on focus;
- state is not color-only;
- Start/Stop targets remain comfortably clickable;
- no focus trap or surprise focus movement occurs;
- support appears only from a real support-eligible failure and exposes no report body.

## 9. Visual Comparison And Brand Distance

Capture metadata-safe GRAF evidence for all 16 state classes in [visual-target.md](./visual-target.md). For every layout-sensitive state, capture both `1280×760` and `1040×680`. Compare each after screenshot with the same GRAF before viewport/state. Then compare the overall hierarchy with the supplied Krisp reference only at the principle level.

Pass criteria:

- the intended reductions and hierarchy changes are visible at matched viewport/state;
- spacing, alignment, typography, borders, radii, focus, and responsive transitions are internally consistent;
- no copied reference string, asset, icon treatment, gradient banner, proprietary flow, or recognizable branded composition appears;
- screenshots contain no private content and are not committed unless generated from synthetic fixtures.

## 10. Full Repository Gate

```sh
infra/scripts/ci-local.sh
```

Expected: exit `0` after focused and live validation are already green.

## 11. Release Boundary

Scoped feature commits are approved after their named validation passes and their staged file list contains no unrelated worktree changes. Do not run production deploy, publish a release, or replace the installed public app without a separate explicit release decision. Record any manual local build/run separately from production evidence.

## 12. Final Implementation Evidence — 2026-07-14

### Automated gates

- Exact expanded focused server command from section 3: `90 passed`, `0 failed`,
  one pre-existing Starlette/httpx deprecation warning in `32.54s`; the set now
  directly includes the compact-upload CSS regression contract.
- Exact expanded focused macOS command from section 4: `117 tests`, `0 failures`;
  the set now directly includes unavailable-state copy, safe retry routing, and
  separate VoiceOver recovery-action contracts.
- Current full macOS suite after the final accessibility correction:
  `619 tests`, `0 failures`; `ContractValidation: PASS`.
- Exact release command from section 5 and the local installer build both exit
  `0`; product `TwoBrainRecApp` builds successfully and the local artifact is
  GRAF `2026.07.14.1`.
- Final full repository gate: `619` Swift tests with `0` failures,
  `ContractValidation: PASS`, `1238 passed`, `4 skipped`, one pre-existing
  deprecation warning for the server, Ruff/compile/compose/evidence scan clean,
  and `ci_local_result=pass`.
- `git diff --check` and ordinary-UI forbidden-copy scans are clean. A final
  scan found one legacy fallback sentence about diagnostics/reporting; it was
  replaced with impact-and-recovery copy and protected by
  `testCustodyFallbackCopyKeepsDiagnosticsOutOfTheUserInterface`.

### Browser and accessibility evidence

- Synthetic embedded cabinet states were exercised in a real browser at
  `988×680` and `1228×760`, corresponding to the `1040×680` and `1280×760`
  app targets after the 52 pt native rail.
- Measured `scrollWidth == clientWidth` at both sizes; the sidebar is `64 px`
  in compact mode and `176 px` at the default width, toolbar controls are
  `36 px`, and meeting rows are `48 px`.
- The post-fix regression recheck at `772×680` (the WebView width with the
  expanded native inspector) and `988×680` measures `Загрузить запись` at
  `40×36 px`, `grid-column: auto`, zero horizontal overflow, and search using
  the remaining toolbar width. The obsolete 100%-width upload rule is deleted.
- At row focus, the accessibility snapshot exposes the row-specific checkbox,
  primary `Открыть встречу …` link, delete action, state, duration, and date.
  Outside reading intent the checkbox/delete controls are not exposed.
- `Escape` closes filters and restores focus to `Фильтры`; outside click closes
  sorting; the contextual checkbox hit area measures `32×32`.
- Final metadata-safe screenshots are kept outside git as
  `implemented-web-988x680-final-v3.png` and
  `implemented-web-1228x760-final-v3.png` in the local Codex visualization
  workspace. They contain only synthetic meeting data.
- The composition uses the existing GRAF wordmark, color tokens, icons, and
  interaction language. No Krisp string, asset, gradient banner, proprietary
  flow, or recognizable branded composition was copied.

### Native runtime evidence and remaining manual boundary

- `build-local-installer.sh` produced GRAF `2026.07.14.1`; the rebuilt
  `GRAF.app` is valid on disk and satisfies its designated requirement with
  expected local ad-hoc signing. `graf-local.pkg` is intentionally unsigned
  for local development and was not installed.
- Source/behavior tests cover ready, permission-required, detected-meeting,
  starting, recording, paused, stopping, saved, cabinet-unavailable, and
  actionable-failure states; separate accessible Pause/Resume/Stop actions,
  direct rail Start/Stop, stable inspector width, active-only meters, and a
  separately reachable recovery button pass.
- An isolated GRAF QA bundle with bundle id
  `pro.2brain.graf.feature104qa` was exercised unlocked at the minimum window.
  The real production shell showed centered human offline copy, a separate
  `Повторить` button, direct compact `Начать запись`, intentional disclosure,
  and expanded `Готово к записи` plus the full-width
  `Начать запись системного звука` action. Retry returned safely to the same
  offline state and did not affect native recording authority.
- A disposable QA host outside the repository and product bundle rendered the
  real production `CaptureControlView`/`CaptureStatusItem` with synthetic
  permission, detected-meeting, starting, recording, paused, stopping, saved,
  and actionable-failure inputs. The complete minimum-window pass and the
  large-window active-recording pass exposed exact accessibility names and
  separate Pause/Resume/Stop actions without starting capture.
- That pass found and corrected five native presentation defects: clipped
  status/action labels, two-column meters overflowing the 308 pt inspector,
  repeated local and detected-meeting summaries, a duplicate Stop during
  finalization, and a saved-state icon/VoiceOver trait that implied hidden or
  selected content. The recheck shows one detected-meeting prompt, full labels,
  vertically contained meters, no redundant local status, no finalizing Stop,
  and one meaningful saved-state announcement.
- No real `Начать запись` click was made because that would capture user audio;
  Start/Pause/Resume/Stop/finalization are covered with synthetic state and
  controller tests. No app replacement, install, deploy, or release occurred.
- T016, T028, T036, and CHK069 are satisfied by the combined evidence: the real
  GRAF shell covered onboarding/idle/offline/retry, the isolated unlocked native
  host covered all synthetic capture views and VoiceOver actions, the browser
  matrix covered both exact embedded target widths, and the invariant 308 pt
  inspector was rechecked in minimum and large native windows. macOS locked
  before one redundant post-build cold-launch screenshot, but no separate view
  path remained untested; the final source, release build, and full gate are
  green.

## 13. Post-Master Integration Evidence — 2026-07-14

Feature 104 was reconciled with current `origin/master`, including the merged
feature `098-calendar-auto-context-match`, before closeout:

- safe server-issued calendar match/context state, retry behavior, and the
  recurring-series previous-meeting pointer remain intact;
- `Ближайшие` is rendered only for a real, authorized future occurrence from
  the recurring series; the main meeting screen does not restore an empty
  calendar placeholder or a duplicate `Подключить календари` call to action;
- capture start still resolves calendar context without restoring a raw local
  recording-path presentation state;
- human failure copy, compact meeting-first navigation, contextual selection,
  and debug-free status presentation remain the feature-104 authority.

Post-reconciliation focused validation:

- server crossover suite: `168 passed`, `0 failed`, with the existing
  Starlette/httpx deprecation warning only;
- macOS crossover suite: `149 tests`, `0 failures`;
- Ruff check and format check: clean;
- conflict-marker and whitespace checks: clean.

Canonical full repository gate after conflict resolution:

- macOS Swift tests: `642 tests`, `0 failures`;
- `ContractValidation: PASS`;
- server: `1427 passed`, `4 skipped`, `0 failed`, with the same existing
  Starlette/httpx deprecation warning;
- Ruff, Python compile, production Compose config, and deployment evidence scan:
  clean;
- PostgreSQL RLS runtime validation remains explicitly skipped when its
  disposable test database is unavailable, as designed by the gate;
- final result: `ci_local_result=pass`.

No production deploy, release publication, package installation, or installed
app replacement was performed during this integration.

## 14. Post-PR Review Evidence — 2026-07-14

The ready PR received an additional code, interaction-contract, and dead-state
review. Every confirmed finding was corrected before the final commit:

- manual-upload titles now strip every explicitly accepted media extension;
- the active-filter count follows the status/access contract and does not count
  a search query;
- removed navigation fields and template branches no longer leave unreachable
  workspace, count, or enabled state behind;
- obsolete bulk-action, tooltip, toolbar, navigation-count, and compact-control
  CSS was deleted;
- the expanded native inspector keeps the embedded status, access, and sort
  controls available instead of hiding them at its WebView width.
- the visible `В обработке` filter includes `submitted` and `processing`, while
  `Нужна помощь` includes `blocked`, `failed`, and `unavailable`, matching the
  status wording shown in rows;
- the collapsed embedded sidebar removes its hidden footer from keyboard and
  accessibility navigation until the user explicitly expands the rail.

Review validation:

- focused server regression set: `105 passed`, `0 failed`, with the existing
  Starlette/httpx deprecation warning only;
- the manual calendar-sync timing scenario now starts from its real user entry
  point — a successfully rendered settings page — and keeps the original
  `<2s` feedback contract; the endpoint performs no provider wait or external
  call;
- the production cabinet rendering was rechecked after CSS cleanup at
  `772×680` and `988×680`: `scrollWidth == clientWidth`, toolbar controls stay
  `36 px` high, search uses the remaining width, and upload, filter, sort, and
  both popovers remain visible without overlap;
- dead-selector and removed-navigation-state scans: `0` findings;
- focused grouped-filter/sidebar regression set: `72 passed`, `0 failed`, with
  the existing Starlette/httpx deprecation warning only;
- focused visible-title/search regression set: `58 passed`, `0 failed`, with
  the existing Starlette/httpx deprecation warning only;
- focused calendar-prompt/custody native regression set: `76 tests`, `0`
  failures;
- final full repository gate: `642` macOS tests with `0` failures,
  `ContractValidation: PASS`, `1430 passed`, `4 skipped`, one existing server
  deprecation warning, Ruff/compile/Compose/evidence checks clean, and
  `ci_local_result=pass`;
- final Spec Kit traceability and code review: no critical blockers, unmapped
  requirements, conflict markers, unsafe ordinary-UI copy, or remaining
  actionable findings.

The two pre-fix full-suite failures were both the pre-existing calendar timing
assertion exceeding `2.000s` by `0.005s` and `0.028s`; all other `1426` tests
passed in both runs. Profiling showed that the test timed a cold app/client
before the settings page a user must open to reach manual sync. The test-only
correction models that entry point and preserves the two-second requirement; it
is not feature-104 product code and remains explicit in the diff and evidence.

The previous-head automated review raised four comments. The compact-popover
comment was already fixed, and the grouped-status and hidden-sidebar-focus
comments produced the regressions above. The proposed raw report-copy fallback
was intentionally not restored: FR-007 and the capture-surface contract require
contextual `Связаться с поддержкой` without exposing report contents in the
ordinary UI; the metadata-only report, redaction, submission, and retry services
remain intact.

The next automated review found four additional cross-surface boundaries. The
compact record action now defers to an active calendar record prompt; actionable
custody summaries include owner, admin, support, and policy-owned next steps;
authoritative titles are preserved; and list search matches the humanized title
shown to the user. Each boundary has a focused regression and the full gate
above was rerun after the fixes.
