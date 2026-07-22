# Quickstart: Meeting List Presentation Contract Validation

Run from the repository root unless a step says otherwise. Use synthetic meeting data only. Never commit real meeting names, participants, transcript/audio content, account details, credentials, tokens, signed URLs, or live local paths.

## 1. Preconditions

```sh
git branch --show-current
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
git status --short
git diff --name-only origin/master...HEAD -- apps/macos
```

Expected:

- branch is `122-meeting-list-presentation-contract`;
- feature paths point to `specs/122-meeting-list-presentation-contract`;
- unrelated changes are absent or explicitly preserved;
- no native macOS file is part of this feature diff.

## 2. Approved Pre-build Target

Use [visual-target.md](./visual-target.md) as the complete pre-build design contract. Figma, Stitch, and other external prototypes are not required.

Before implementation, confirm that the target defines:

- exact toolbar, row, batch, empty, recovery, and deletion copy;
- one total status priority;
- open versus selection keyboard semantics;
- `1280×760` and `1040×680` geometry;
- all 16 synthetic evidence classes;
- browser/embedded parity, privacy, accessibility, and clean-room boundaries.

Real GRAF/Krisp screenshots are research inputs only and remain outside git.

## 3. Focused Baseline And Regression Tests

From the repository root through the isolated PostgreSQL runner:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_hx_fragments.py \
  tests/integration/test_cabinet_hx_delete_feedback.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_playback_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_cabinet_static_assets_contract.py
```

Expected after implementation:

- total status precedence and ready-state silence pass;
- generated titles, trusted meeting/update time, and default sort pass;
- one heading/search/filter/sort/upload hierarchy and refined count pass;
- open never selects and explicit selection never opens;
- contextual/batch/delete/live-region/focus behavior passes;
- browser and embedded HTML use the same copy and semantics;
- playback/calendar detail truth remains available without ordinary-row noise;
- no private-content egress regression.

Record the pre-change and post-change test count/result in this document during implementation. A failing baseline is investigated before product code changes.

### Pre-change record — 2026-07-21

- The direct `pytest` form originally written here ran the non-database subset but could not start database-backed tests: `115 passed`, `53 errors`, `2 warnings` in `1.07s`; every error had the same setup cause, missing `TWOBRAIN_DATABASE_URL`, and pointed to the repository runner.
- The corrected isolated-runner command above passed before product-code changes: `168 passed`, `2 warnings` in `130.46s`; runner phase `focused` passed in `133s` and removed its disposable PostgreSQL container.
- Warnings were environment/dependency deprecations only: pytest assertion rewriting for the already imported test fixture and the existing Starlette `TestClient`/`httpx` transition warning.
- Result: baseline is green; no feature-owned failure was present before implementation.

## 4. Focused Query, Calendar, Playback, And Deletion Compatibility

From `apps/server`:

```sh
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_meeting_deletion_workflow.py \
  tests/integration/test_cabinet_web_access_states.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_deletion_no_secret_leakage.py
```

Expected:

- calendar ambiguity remains actionable while matched/no-context states remain truthful in detail;
- playback preparing/unavailable routes remain truthful and ready playback stays usable;
- authorization, CSRF, bounded deletion semantics, and metadata-safe access failures remain unchanged.

## 5. Static Presentation Audit

```sh
rg -n "Готово|Аудио готово|Без календарного контекста|Из календаря|Выбрано вами|Контекст убран вами" \
  apps/server/src/twobrain_rec_server/cabinet/rendering.py \
  apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html

rg -n "Star|Tag|Save for later|Mark as unread|New Folder|Reactivate|Upgrade|Пригласить|Пробный период" \
  apps/server/src/twobrain_rec_server/cabinet

node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

Expected:

- ordinary list rendering has no independent ready/playback/calendar-normal tokens;
- permitted matches are limited to explicit detail/recovery mappings or tests proving absence;
- no Krisp copy/feature appears in GRAF;
- JavaScript parses successfully.

## 6. Synthetic Browser And Embedded Matrix

Render the same synthetic `MeetingListResponse` fixtures through `render_meeting_list_page(..., embedded=False)` and `embedded=True`. Exercise:

1. ready list;
2. priority collisions;
3. measured and unmeasured upload;
4. processing;
5. calendar choice;
6. audio preparing and unavailable;
7. failed/recovery;
8. hover and keyboard focus;
9. single and multiple selection;
10. deletion accepted and partial failure;
11. first empty list;
12. refined no-results;
13. loading;
14. offline, service unavailable, and session expired;
15. long title and no-date rows;
16. minimum window, keyboard, VoiceOver/accessibility tree, increased contrast, and Reduce Motion.

For every state assert:

- zero or one compact status;
- ready rows have zero normality badges;
- exact copy from [visual-target.md](./visual-target.md);
- no private/generated identifier or reason code;
- open and selection remain separate;
- browser/embedded visible and accessible copy match.

## 7. Layout And Interaction Evidence

Capture synthetic before/after evidence outside the repository first. Commit only deliberately reviewed synthetic artifacts if tasks require repository evidence.

Required viewports:

- `1280×760` for every state class;
- `1040×680` for toolbar, ready/exceptional rows, hover/focus, selection, empty/recovery, and long-title states.

Required checks:

- no horizontal scroll, overlap, clipped critical action, or shifted title/date zone;
- ready row 48 px; exceptional row no more than the target's 60 px;
- contextual targets at least 32×32 CSS px;
- visible focus indicator equivalent to at least a 2 CSS-pixel perimeter;
- status/action meaning does not rely only on color;
- `prefers-reduced-motion: reduce` disables optional motion;
- increased-contrast mode preserves control/state boundaries.

## 8. Keyboard And Accessibility-Tree Walkthrough

For the first ordinary row and one exceptional row:

1. Tab to the row/link and confirm the full safe title, duration, optional compact status, and time are available once.
2. Press `Enter`; confirm the meeting opens and checkbox state is unchanged.
3. Return, focus the row/selection control, and press `Space`; confirm selection changes without navigation or page scrolling.
4. Tab through contextual checkbox/open/action/delete controls; confirm names are row-specific and focus is visible.
5. Select a second row; confirm `Выбрано: 2`, `Выбрать все`, `Снять выбор`, and `Удалить` are reachable.
6. Cancel deletion with `Escape`; confirm focus returns to the invoking control.
7. Accept synthetic deletion; confirm feedback is announced without focus theft and focus moves next → previous → list anchor.
8. Replace the list through HTMX while focused/selected; confirm surviving selection/focus is reconciled predictably.

Forbidden accessibility-tree content:

- raw status/reason codes;
- local recording IDs or paths;
- duplicated `Готово`/`Аудио готово`/calendar-normal copy;
- controls marked hidden but still focusable;
- meeting metadata after session expiry/access revocation.

## 9. Clean-room Review

Compare final GRAF evidence with the supplied Krisp reference only for general hierarchy, density, and progressive disclosure. Record zero instances of copied:

- wording;
- icons/assets;
- palette/gradient;
- branded composition;
- folders, tags, favorites, save-later, unread, sharing, billing, or upcoming flows.

The result must still read as GRAF and use only existing supported capability.

## 10. Full Repository Gate

From repository root:

```sh
infra/scripts/ci-local.sh
```

Expected: exit `0`, with Swift, server, contract, lint/compile, and repository checks green.

If the full gate exposes an unrelated pre-existing failure, record exact evidence and prove the feature-focused suites independently; do not silently weaken the gate.

## 11. Handoff Gate

Before requesting a product-code commit/PR decision:

- every desired task is `[X]` only after its named evidence exists;
- `$speckit-analyze` has no critical findings;
- associated GitHub issues have status/evidence comments but are not falsely closed;
- `git diff --check` passes;
- no new dependency, migration, public API change, native capture change, secret, or private screenshot is present;
- implementation code remains uncommitted until explicit user approval;
- no deploy, release, installer replacement, or production rollout has occurred.

## 12. Implementation Evidence Record

### Boundary and synthetic identifiers — 2026-07-21

- Branch and feature paths were confirmed as `122-meeting-list-presentation-contract` and `specs/122-meeting-list-presentation-contract`.
- `git diff --name-only origin/master...HEAD -- apps/macos` returned no paths before implementation.
- Native capture, database, public API, dependency, migration, release, and deploy behavior remain outside this slice.
- Synthetic state identifiers: `ready`, `priority-collision`, `upload-measured`, `upload-unmeasured`, `processing`, `calendar-choice`, `audio-preparing`, `audio-unavailable`, `failed-recovery`, `hover-focus`, `selection`, `deletion`, `first-empty`, `refined-empty`, `network-session-recovery`, and `long-title-no-date-accessibility`.
- Required viewports: `1280×760` for all 16 classes and `1040×680` for every layout-sensitive class named in §7.
- Evidence policy: synthetic meeting metadata only; no real screenshots, names, participant data, audio, transcript, account data, credentials, tokens, IDs, local paths, or signed URLs.

### Foundation and User Story 1 — 2026-07-21

- Pure query/row presentation values are frozen and covered by a deterministic unit matrix; unknown list sort normalizes to `started_desc`, while the public API's explicit/default `updated_desc` contract remains available.
- Browser and embedded routes default to `Сначала новые`; undated rows remain last for both recording-date directions.
- Status comprehension matrix passed for all canonical outcomes: `Удаляется`, `Не удалось обработать`, `Нужен выбор`, `Сохранено на Mac`, measured/unmeasured `Отправляем`, `Обрабатывается`, `Аудио готовится`, `Без аудио`, `Готово с ограничениями`, and silent normal readiness. Each row projects zero or one status and a separate action only for calendar choice.
- Ordinary list rows contain none of `Готово`, `Аудио готово`, or calendar-normal provenance; detail/API regression checks retain matched, declined, cleared, and playback-recovery truth.
- Toolbar check passed with one `Мои встречи`, search, grouped filter trigger, current sort label, `Загрузить запись`, and contextual `Найдено: N`; duplicate sort/list headings are absent.
- Focused US1 command used the isolated PostgreSQL runner for `test_cabinet_view_models.py`, `test_cabinet_web_shell.py`, `test_cabinet_meeting_list.py`, `test_cabinet_contract.py`, plus the named calendar/playback regressions: `152 passed`, `2 warnings` in `75.49s`; runner phase passed in `79s` and removed its disposable container.
- The same two baseline dependency warnings remained; no new warning or private evidence was introduced.

### User Story 2 — 2026-07-21

- Tests-first proof started with three expected failures for semantic list rows, stable contextual columns, and JavaScript open/selection reconciliation; the same focused cases then passed after implementation.
- The collection now exposes one ordered list of list items. Each row associates its safe title with duration, optional compact status, and time, while keeping a real primary link, real checkbox, row-specific delete button, and separate calendar action.
- A local headed Playwright walkthrough at `1280×760` used only four synthetic titles. Pointer activation on the readable row opened the synthetic detail route; focused-row `Space` selected without navigation; focused-row `Enter` opened; clearing selection removed batch mode.
- The accessibility snapshot exposed `Выбрано: 1`, `Выбрать все`, `Снять выбор`, and visible `Удалить` with accessible name `Удалить выбранные встречи`. Focused/selected row controls were named `Выбрать встречу Проектный синк` and `Удалить встречу Проектный синк`; hidden controls were `tabindex=-1` and `aria-hidden=true` before contextual reveal.
- An HTMX search replacement reduced four rows to the surviving selected row and retained exactly that selection and `Выбрано: 1`; clearing it removed the toolbar. The row title/date zones did not shift on focus or selection because both contextual columns remain reserved.
- `node --check` passed for the cabinet script. The US2 compatibility suite covering the web shell, static assets, frontend foundation, and browser/embedded meeting-list integration passed: `92 passed`, `2 warnings` in `47.36s`; runner phase passed in `50s` and removed its disposable PostgreSQL container.
- The same two baseline dependency warnings remained; the walkthrough introduced no real meeting data, private content, credentials, identifiers, or production access.

### User Story 3 — 2026-07-21

- Tests-first proof began with the expected missing-state result: `6 failed, 2 passed`. After the smallest rendering/client changes, the named waiting, empty, access, recovery, and deletion cases passed: `11 passed`, `2 warnings` in `24.94s`.
- Measured and unmeasured upload, processing, calendar choice, audio preparation/absence, and failed processing each render one total compact status; terminal rows render no stale upload meter. First-empty and refined-empty states use distinct exact copy without hiding the persistent upload action.
- HTMX loading exposes one polite `Загружаем встречи…` status. Synthetic service `503`, session `401`, and browser-offline failures replaced the collection with one metadata-safe state and one applicable action; no cached title, date, status, identifier, path, or transcript remained. Retry restored the current query, and expired-session recovery linked to the bounded sign-in route.
- Accepted deletion announces exactly one line above the collection: `Запись удалена из списка. Очистка данных GRAF продолжается.` Cancelling with `Escape` returned focus to the invoking delete control; accepted deletion moved focus next → previous → `Мои встречи` when the collection became empty.
- When the final visible rows are deleted, both surfaces immediately replace the empty ordered list with `Пока нет встреч` / `Начните запись или загрузите готовый файл.`, hide batch mode, retain the accepted feedback, and focus `Мои встречи`; no refresh is required.
- A headed Playwright partial-failure walkthrough selected two synthetic rows. One successful row was removed, the failed row remained selected, and the dialog stayed open with `Не удалось удалить 1 запись. Попробуйте ещё раз.` plus `Повторить`; no private failure reason entered the page.
- Access-revoked rendering now says `Встреча больше недоступна` and offers only the bounded return action without repeating meeting metadata.
- `node --check` passed. The US3 rendering/static/privacy/deletion/access suite passed: `160 passed`, `2 warnings` in `49.66s`; runner phase passed in `53s` and removed its disposable PostgreSQL container.
- The same two baseline dependency warnings remained; all browser evidence used four synthetic titles on a loopback-only server and no production/private data.

### User Story 4 — 2026-07-21

- Tests-first proof began with the expected `2 failed`: rows had no explicit exceptional-height class/variable, and forced-colors selection had no explicit system-color cue. The same named tests passed after the bounded class/CSS change: `2 passed`, `2 warnings`.
- A headed Playwright matrix exercised all 16 named evidence classes on both browser and embedded surfaces at `1280×760` (`32` rendered scenarios). Every row had zero or one compact status; every ready row measured `48px`, every exceptional row measured `56px`, every contextual target measured at least `32×32px`, and both document and main-region horizontal overflow stayed false.
- The layout-sensitive matrix exercised ready, exceptional, hover/focus, selection, deletion, first-empty, refined-empty, service recovery, and long-title/no-date states on both surfaces at `1040×680` (`18` rendered scenarios). Document, main, and toolbar overflow stayed false; the final upload control remained inside the viewport (`1006.73px` browser and `1014px` embedded right edge within `1040px`), and critical controls stayed visible.
- The long synthetic title retained its full accessible open name while the visual line remained bounded, and the separate trusted time description said `Без даты`. Accessibility relations included title plus duration, the optional one status, and time exactly once.
- Keyboard parity passed on both surfaces: row `Space` selected one item without navigation or scroll, row `Enter` opened detail without changing selection semantics, and deletion cancellation with `Escape` returned focus to the row-specific `Удалить встречу …` control. Selection exposed the same `Выбрано: 1` batch state.
- Loading, session-expired, and offline behavior matched on both surfaces. Loading exposed only `Загружаем встречи…`; session recovery had one sign-in link with the correct bounded return path; offline recovery had one retry and `Запись на Mac продолжает работать.` No recovery DOM retained a synthetic title or row.
- With Reduce Motion enabled, row transition and animation durations computed to `1e-06s`. Forced Colors preserved a `2px` focus outline and system `Highlight` selection marker; `prefers-contrast: more` used the strengthened focus/muted tokens and a `2px` selected outline on both surfaces.
- Two privacy-safe representative screenshots were visually inspected outside git: browser selection at `1280×760` and embedded long-title/no-date at `1040×680`. Neither showed overlap, clipping, shifted title/date columns, inaccessible critical actions, or reference-brand expression.
- Clean-room audit found zero Krisp names, wording, assets, branded palette/gradient, or unsupported folder/tag/favorite/save-later/unread/sharing/billing/upcoming flows in the changed cabinet surface. Existing GRAF wordmark, icons, navigation, dark tokens, and supported upload/delete/calendar behavior remain the product language.
- The full US4 web-shell/static-assets suite passed: `72 passed`, `2 warnings` in `0.14s`; runner phase passed in `3s` and removed its disposable PostgreSQL container. The same two baseline dependency warnings remained.

### Focused and compatibility closeout — 2026-07-21

- The complete §3 focused command passed: `198 passed`, `2 warnings` in `138.94s`; runner phase passed in `143s` and removed its disposable PostgreSQL container.
- The complete §4 calendar/playback/deletion/access compatibility command passed through the same isolated runner: `78 passed`, `2 warnings` in `111.70s`; runner phase passed in `115s` and removed its disposable PostgreSQL container.
- The final client-empty regression passed independently: `1 passed`, `2 warnings` in `0.26s`; runner phase passed in `3s`. JavaScript syntax validation passed after the final change.
- The §5 ordinary-row audit returned zero ready/playback/calendar-normal matches in list rendering, and the clean-room forbidden-copy audit returned zero Krisp/marketing/proprietary-flow matches in cabinet source.
- All focused runs showed only the same baseline pytest assertion-rewrite and Starlette `TestClient`/`httpx` transition warnings; there was no feature-owned warning or failure.

### Full repository gate — 2026-07-22

- The first full run correctly caught one feature-owned stale calendar-list expectation: a legacy integration test still required the normal `Из календаря` token that Feature 122 intentionally removes from ordinary rows. The expectation was aligned without weakening immutable-roster, detail, browser/embedded, or privacy assertions; its focused rerun passed (`1 passed`, `2 warnings` in `3.11s`).
- A complete second `infra/scripts/ci-local.sh` run exited `0` with `ci_local_result=pass`.
- macOS legacy-audio guard passed; Swift build passed; all `592` Swift tests passed with zero failures; `ContractValidation: PASS`.
- Server parallel phase passed with `2043 passed`, `1 skipped`, and `10` existing dependency warnings in `276.75s`; strict PostgreSQL phase passed with `35 passed`, `1 skipped`, `2044 deselected`, and `2` existing warnings in `7.05s`. The isolated container was removed.
- Server lint reported `All checks passed`; Python compile, production Compose configuration, and deployment-evidence scan (`files=7`) passed.
- The local RLS validation boundary truthfully reported `blocked`/`ready_for_production_truth=false` because no live production database or destructive probe was supplied. The CI script treats that as the expected local non-deploy boundary and still passed; Feature 122 neither weakens nor claims production RLS evidence.
- No release, installer replacement, live production probe, or deploy was performed.

### Approval-ready handoff — 2026-07-22

- A final read-only `$speckit-analyze` pass found no critical, high, or medium cross-artifact findings: `36` functional requirements and `12` success criteria are covered by `38` dependency-ordered tasks across all four user stories; both constitution checks remain `PASS`, all requirement-quality checklist items are complete, and no unresolved placeholder remains.
- `git diff --check` passed. Both the current worktree diff and `origin/master...HEAD` contain `0` paths under `apps/macos`; the changed-path audit found `0` migration, dependency/lockfile, public API/schema, untracked, or media-evidence paths.
- The added-line secret scan found no secret value. Its only lexical match was the literal forbidden marker `signed_url` in `test_cabinet_no_secret_content_egress.py`, where the test proves that marker is absent from recovery output.
- JavaScript syntax validation passed with `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- GitHub issues `#4088` through `#4125` were re-read as one bounded set: `38/38` remain open and `38/38` contain the Feature 122 implementation/validation evidence comment. The repository issue-canon validator passed: `github-issue-canon: OK (136 Spec Kit issue(s) checked)`.
- All `38/38` implementation tasks now have named evidence. Documentation checkpoint commits remain separate; the product-code diff is intentionally uncommitted pending explicit user approval.
- No product commit, push, PR, merge, release, installer replacement, production probe, or deploy was performed by this handoff.

### Independent review fixes — 2026-07-22

- Independent architecture, code, frontend, product, accessibility, and privacy review found and closed the remaining list-boundary defects before integration: terminal upload states no longer look in progress; visible projected titles participate in search and title sort; whitespace and overlong queries preserve truthful empty/recovery states; submitted uploads remain observable; deletion refreshes the refined count; session expiry scrubs upcoming/upload/search/list metadata; neutral rows announce their time once; selection padding no longer opens a row; and undated updated-sort fallbacks are deterministic.
- A subsequent route/privacy pass kept the ambiguity action on the durable candidate set via `<detail>#calendar-context-chooser`; `?calendar_context_action=change` remains reserved for correcting an already selected context. The same pass disabled HTMX history snapshots for the private meeting list, purged any legacy `htmx-history-cache` without reading or writing meeting data in first-party storage, and added `Cache-Control: private, no-store` to cabinet HTML responses.
- The calendar-choice contextual action now has a `32px` minimum target. Current-run embedded-browser measurement at `1040×680` caught a `66px` exceptional row; the bounded status-row padding fix reduced it to `58px` while preserving the `32px` action, stable title/date columns, and zero horizontal overflow. Keyboard `Space` selected without navigation and exposed the row-specific batch/accessibility names with a visible `2px` focus indicator.
- The complete isolated focused review suite passed after these fixes: `206 passed`, `2 warnings` in `141.60s`. A final changed-surface check then passed `19` targeted contracts/tests, Ruff, JavaScript syntax validation, and `git diff --check`; only the two documented dependency warnings remained.
- All visual evidence used synthetic meeting data and remains outside git. The same-tool clean-room comparison confirmed that GRAF retains its own wordmark, dark tokens, navigation, wording, and supported actions while applying only the general density, hierarchy, and progressive-disclosure lessons from the Krisp reference.

### Final review and repository gate — 2026-07-22

- The final §3 isolated PostgreSQL review suite passed: `202 passed`, `2 warnings` in `126.44s`; Ruff, JavaScript syntax validation, and `git diff --check` also passed.
- The final §4 calendar/playback/deletion/access compatibility suite passed through the isolated runner: `78 passed`, `2 warnings` in `103.82s`; runner phase passed in `107s` and removed its disposable PostgreSQL container.
- Independent correctness/security review found one last privacy-recovery defect: WebKit can reject `history.replaceState` for a neutral recovery path. The mutation is now best-effort, so that exception cannot interrupt private DOM and HTMX-history scrubbing; the focused regression contract passed.
- A later Ponytail pass removed three duplicate string assertions; its immediate re-review reported exactly `Lean already. Ship.` The final independent correctness/security re-review then found no actionable regression and independently repeated the focused (`202 passed`, `2 warnings` in `150.49s`) and compatibility (`78 passed`, `2 warnings` in `103.98s`) suites; Ruff, JavaScript syntax, and diff checks remained clean.
- The first post-review full CI run correctly caught two assertions from one stale Feature 058 runtime-evidence check, which prohibited every `sessionStorage` reference. The evidence now distinguishes persistence from privacy cleanup: first-party code still cannot write meeting state, while removing the two HTMX history keys is required. The evidence script and both contract tests passed after the correction.
- One immediate retry stopped before server tests because its disposable PostgreSQL container did not become ready; the runner removed the failed container. A clean retry then completed successfully with `ci_local_result=pass`.
- The successful full gate passed the legacy-audio guard, Swift build, all `594` Swift tests, and `ContractValidation`. Server parallel phase passed with `2047 passed`, `1 skipped`, and `10` existing dependency warnings in `257.71s`; strict PostgreSQL phase passed with `35 passed`, `1 skipped`, `2048 deselected`, and `2` existing warnings in `6.38s`.
- Server lint, Python compile, production Compose validation, and deployment-evidence scan (`files=7`) passed. The local RLS boundary remained truthfully `blocked` because no live production/destructive probe was supplied; this is the expected pre-deploy boundary and was not weakened.
