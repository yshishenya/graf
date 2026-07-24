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
- all 16 synthetic evidence classes, including distinct workspace-reselection and access-denied recovery states;
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
- Synthetic state identifiers: `ready`, `priority-collision`, `upload-measured`, `upload-unmeasured`, `processing`, `calendar-choice`, `audio-preparing`, `audio-unavailable`, `failed-recovery`, `hover-focus`, `selection`, `deletion`, `first-empty`, `refined-empty`, `network-session-workspace-access-recovery`, and `long-title-no-date-accessibility`.
- Required viewports: `1280×760` for all 16 classes and `1040×680` for every layout-sensitive class named in §7; the recovery class includes separate workspace-reselection (`Нужно выбрать пространство`) and access-denied (`Нет доступа к встречам`) states.
- Evidence policy: synthetic meeting metadata only; no real screenshots, names, participant data, audio, transcript, account data, credentials, tokens, IDs, local paths, or signed URLs.

### Foundation and User Story 1 — 2026-07-21

- Pure query/row presentation values are frozen and covered by a deterministic unit matrix; unknown list sort normalizes to `started_desc`, while the public API's explicit/default `updated_desc` contract remains available.
- Browser and embedded routes default to `Сначала новые`; undated rows remain last for both recording-date directions.
- Status comprehension matrix passed for all canonical outcomes: `Удаляется`, `Не удалось обработать`, `Нужен выбор`, `Сохранено на Mac`, measured/unmeasured `Отправляем`, `Обрабатывается`, `Аудио готовится`, `Без аудио`, `Готово с ограничениями`, and silent normal readiness. Each row projects zero or one status and a separate action only for calendar choice.
- Ordinary list rows contain none of `Готово`, `Аудио готово`, or calendar-normal provenance; detail/API regression checks retain matched, declined, cleared, and playback-recovery truth.
- Toolbar check passed with one `Мои встречи`, search, grouped filter trigger, current sort label, `Загрузить запись`, and a contextual truthful result count (`Найдено: N` or bounded `Найдено: больше N`); duplicate sort/list headings are absent.
- Focused US1 command used the isolated PostgreSQL runner for `test_cabinet_view_models.py`, `test_cabinet_web_shell.py`, `test_cabinet_meeting_list.py`, `test_cabinet_contract.py`, plus the named calendar/playback regressions: `152 passed`, `2 warnings` in `75.49s`; runner phase passed in `79s` and removed its disposable container.
- The same two baseline dependency warnings remained; no new warning or private evidence was introduced.

### User Story 2 — 2026-07-21

- Tests-first proof started with three expected failures for semantic list rows, stable contextual columns, and JavaScript open/selection reconciliation; the same focused cases then passed after implementation.
- The collection now exposes one ordered list of list items. Each row associates its safe title with duration, optional compact status, and time, while keeping a real primary link, real checkbox, row-specific delete button, and separate calendar action.
- A local headed Playwright walkthrough at `1280×760` used only four synthetic titles and proved pointer activation, selection isolation, clearing, and batch behavior. Its earlier custom focused-row `Enter`/`Space` mechanics were superseded by the fourteenth review correction: the final contract uses native link `Enter` and checkbox `Space`, covered by the final semantic/static/runtime suite below.
- The accessibility snapshot exposed `Выбрано: 1`, `Выбрать все`, `Снять выбор`, and visible `Удалить` with accessible name `Удалить выбранные встречи`. Focused/selected controls use the safe title plus trusted time (for example, `Выбрать встречу Проектный синк, 16 июн, 08:00`). The earlier `tabindex=-1`/`aria-hidden=true` disclosure was removed in the fourteenth correction; final native controls remain in the tab/accessibility sequence and reveal through `focus-within`.
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
- Keyboard parity passed on both surfaces for selection, opening, cancellation, and the same `Выбрано: 1` batch state. The final fourteenth-review contract delegates `Enter` to the native primary link and `Space` to the native checkbox; deletion cancellation with `Escape` still returns focus to the row-specific `Удалить встречу …` control.
- Loading, session-expired, workspace-reselection, access-denied, and offline behavior matched on both surfaces. Loading exposed only `Загружаем встречи…`; session recovery had one sign-in link with the correct bounded return path; workspace reselection had only `Войти и выбрать пространство`; access denial had no action; offline recovery had one retry and `Запись на Mac продолжает работать.` No recovery DOM retained a synthetic title or row.
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
- The calendar-choice contextual action now has a `32px` minimum target. Current-run embedded-browser measurement at `1040×680` caught a `66px` exceptional row; the bounded status-row padding fix reduced it to `58px` while preserving the `32px` action, stable title/date columns, and zero horizontal overflow. Final native checkbox `Space` selection preserves the same row-specific batch/accessibility names and visible `2px` focus indicator.
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

### Full PR review correction loop — 2026-07-22

- A fresh review of the complete `origin/master...HEAD` diff found five actionable P2 defects that narrower changed-surface reviews had missed: coarse-pointer controls could remain visually transparent; client-only deletion could underfill or falsely empty a capped 50-row result set; an authoritative title equal to `Запись без названия` could be rewritten; the select-all checkbox's visible and accessible names diverged after full selection; and the reset control hid its visible label at regular desktop width.
- Touch/coarse-pointer CSS now overrides the exact higher-specificity visually quiet selector. The final controls need no JavaScript focusability reconciliation: hover, `focus-within`, selected state, and coarse-pointer media control only visibility while native semantics remain available.
- Successful deletion now submits the current server-owned search/filter/sort form and swaps the authoritative list fragment. This refills capped results, preserves partial-failure selection, keeps accepted feedback outside the swapped region, and restores focus next → previous → list title after the refreshed DOM arrives; count and empty-state truth are no longer derived from the truncated client DOM.
- `meeting_list_title()` now collapses the fallback sentinel only for non-authoritative sources. `user_confirmed`, `calendar`, and `upload_provided` values are preserved through visible rendering, search, sort, and accessible naming; the integration regression searches the exact fallback-looking authoritative title.
- The select-all visible copy now changes between `Выбрать все` and `Снять выбор` together with an accessible name that contains the same visible wording. The reset label remains visible at normal width and compacts only under the existing `1120px` constrained-layout breakpoint.
- The first correction run passed all product behavior but correctly exposed one stale static expectation for the removed client-only empty renderer: `170 passed`, `1 failed`, `2 warnings`. After aligning that test to the server-refill contract, the fast unit/static rerun passed `148 passed`, `2 warnings`.
- The complete §3 isolated feature suite then passed `207 passed`, `2 warnings` in `132.75s`; runner phase passed in `135s` and removed its disposable PostgreSQL container. Ruff, JavaScript syntax, and `git diff --check` also passed, with only the two previously documented dependency warnings.

### Second full PR review correction loop — 2026-07-22

- A new review of the complete `origin/master...HEAD` diff found four additional P2 boundary defects: generated neutral recordings were no longer searchable by the date/time still visible in their row; embedded `403 reselect-space` responses were mislabeled as an expired session; recovery removed the loading/current shell needed by a retry; and the explicit sub-`620px` time column clipped full date/update labels.
- The web search projection now reuses the exact visible trusted time formatter for neutral generated titles, including the recording timezone offset and selected meeting/update time basis. Synthetic regressions prove discovery by `14`, `июл`, and `02:30` without exposing or matching the technical identifier.
- HTMX recovery now distinguishes `401`, workspace reselection, and independent access denial. All access-loss paths scrub cached meeting metadata; workspace reselection uses the existing bounded sign-in path, a generic `403` offers no unusable sign-in action, and recovery preserves or safely reconstructs the loading/current shell so a retry displays `Загружаем встречи…` and cannot be submitted repeatedly from the visible recovery state.
- Below the supported desktop target, the full time label moves under the content column instead of entering a fixed `52px` column. The supported `1280×760` and `1040×680` geometry remains unchanged.
- The focused correction set passed `187 passed`, `2 warnings` in `100.92s`; runner phase passed in `106s` and removed its disposable PostgreSQL container. A shortcut direct pytest invocation then truthfully stopped its database-backed subset at setup (`151 passed`, `12 errors`) because it lacked `TWOBRAIN_DATABASE_URL`; no product assertion failed, and the documented isolated runner was used for the authoritative result.
- The complete §3 isolated feature suite passed `209 passed`, `2 warnings` in `175.65s`; runner phase passed in `181s` and removed its disposable PostgreSQL container. Ruff, JavaScript syntax, and `git diff --check` remained clean, with only the two previously documented dependency warnings.

### Third full PR review correction loop — 2026-07-22

- The next complete-diff review found five remaining boundaries: plain-fetch deletion did not scrub the list on `401/403`; named rows were excluded from visible-time search; title-plus-date queries were not matched against the combined visible row; an authoritative refresh could leave a retry dialog with no pending rows; and WebKit/VoiceOver could lose native list semantics after marker suppression.
- Deletion now routes authorization loss through the same session/workspace/access recovery used by HTMX, aborts the batch, closes the modal, and replaces cached meeting metadata. A post-refresh reconciliation closes a stale retry dialog when the server has already removed every pending row, or updates its count and copy when retryable rows survive.
- Visible web search now applies the exact recording-timezone projection to named as well as generated rows and includes the combined visible title/time string. The final Python projection remains authoritative; the later sixth review loop replaces the formerly unbounded projected-field path with a SQL-compatible coarse visible-row predicate before per-meeting work.
- The ordered meeting collection now carries an explicit `role="list"`, preserving list semantics in Safari/WKWebView with VoiceOver while CSS suppresses visual markers.
- The first isolated correction run passed `208` product and regression tests and exposed one stale static string expectation after the shared authorization helper refactor (`1 failed`, `2 warnings` in `171.83s`); the isolated container was removed. The exact failed contract plus three adjacent interaction/semantics contracts then passed (`4 passed`, `2 warnings`), followed by clean Ruff, JavaScript syntax, and `git diff --check` results.
- The complete §3 isolated feature suite was then repeated from the corrected tree and passed `209 passed`, `2 warnings` in `173.27s`; runner phase passed in `178s` and removed its disposable PostgreSQL container.

### Fourth full PR review correction loop — 2026-07-22

- The next complete-diff trace exposed one authorization-boundary defect: a generic deletion `403 deletion_forbidden` was treated as loss of access to the whole list. The same pass confirmed that read-only shared/team rows still advertised selection and deletion controls even though the server rejected that lifecycle action.
- Row rendering now projects lifecycle controls only for an owner or a privileged workspace viewer. Read-only rows keep inert contextual spacers, so title/date geometry remains stable without presenting an action that cannot succeed; select-all and batch counts operate only on selectable rows.
- Plain-fetch deletion now parses the bounded problem code before choosing recovery. Session, workspace, device, and access loss still close the dialog and scrub private list metadata; `deletion_forbidden` stays a row-level failure and preserves the rest of the list. Transient offline/service recovery also preserves surviving selection, while authorization recovery clears it.
- The targeted rendering/static/privacy/read-only set passed `90 passed`, `2 warnings` in `36.55s`; runner phase passed in `40s` and removed its disposable PostgreSQL container.
- The complete §3 isolated feature suite passed `210 passed`, `2 warnings` in `174.00s`; runner phase passed in `178s` and removed its disposable PostgreSQL container. Ruff, JavaScript syntax, and `git diff --check` remained clean, with only the two previously documented dependency warnings.

### Fifth full PR review correction loop — 2026-07-22

- The next independent complete-diff review reported seven remaining interaction and accessibility boundaries: two revocation problem codes were classified too broadly; embedded manual upload could not signal workspace reselection through its API response header; partial deletion feedback was confined to the retry dialog; visible duration was absent from search; retry and post-deletion focus could be lost; and polled upload progress changed without a bounded live announcement.
- Authorization recovery now classifies `auth_session_invalid` as session recovery and `device_untrusted` as access recovery. A `workspace_scope_denied` response from the current `/desktop/` surface uses workspace recovery even when the manual-upload API cannot emit the list route's `reselect-space` header. Every authorization path continues to scrub list, upload, progress-announcement, feedback, and history metadata.
- Visible search projection now includes the exact formatted duration independently and in title/duration/time combinations. Regressions cover `14 мин`, `1 ч 14 мин`, and `Проектный синк 1 ч 14 мин 14 июл`; the visible substring contract intentionally allows `14 мин` to match `1 ч 14 мин` as well.
- A retry moves focus to the polite loading state, then to the refreshed `Мои встречи` heading on success or to the replacement recovery action on failure. After a successful deletion refresh, both the next and previous row identifiers survive until the authoritative DOM arrives, and focus chooses the first neighbor that still exists.
- Mixed batch deletion now publishes a safe aggregate above the list while retaining the retry dialog for failed rows. Polled upload progress keeps its native progressbar and announces only changed 10% buckets through a persistent polite live region; the live-region text and bucket map are cleared on session/workspace/access recovery.
- The initial correction suite found one invalid negative test assumption: `14 мин` correctly matched the visible `1 ч 14 мин` substring. After aligning that assertion, the named regression passed independently (`1 passed`, `2 warnings` in `3.91s`).
- The complete §3 isolated feature suite then passed `213 passed`, `2 warnings` in `172.61s`; runner phase passed in `177s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no feature-owned warning, private data, production access, or release action was introduced.

### Sixth full PR review correction loop — 2026-07-22

- The next independent complete-diff review found seven final candidate boundaries: a manual-upload draft retained private file/title state after authorization loss; neutral row selection/deletion names were ambiguous; projected-field search could expand into per-meeting query work; HTMX `403` recovery ignored the problem code; a failed authoritative deletion refresh could lose focus; a capped page was mislabeled as the total result count; and the unchanged count could be re-announced every second with upload polling.
- Session/workspace/access recovery now closes and clears both open and closed manual-upload drafts, including the selected `File`, entered title, duration, generated local ID, and preview. HTMX recovery parses the same safe problem code as plain fetch and routes `auth_session_invalid` to the bounded sign-in state instead of a generic denial.
- Select and delete accessible names now include the safe title plus trusted time, disambiguating repeated `Запись` and `Загруженная запись` rows. If the post-delete refresh fails, focus moves to the surviving next/previous row, the applicable recovery action, or `Мои встречи`, and pending focus state is consumed exactly once.
- Visible title/duration/time search now applies a PostgreSQL-compatible coarse projection before access/media/workflow projection, while the existing Python matcher remains authoritative. A synthetic `03:30` miss proves that no per-meeting access or media lookup runs; exact `Запись`, `14 мин`, `1 ч 14 мин`, title/date, and title/duration/date queries remain discoverable.
- For non-title sorts, the bounded list reads one extra authorized match only to distinguish complete from truncated output; title sorting uses its already-materialized matching set for the same flag. The public API shape remains unchanged; refined UI copy is `Найдено: N` or truthful `Найдено: больше N`. A persistent live region announces intentional refinements; one-second polling may replace the visible count but does not update that announcer, and authorization recovery invalidates a queued announcement.
- The first changed-surface run passed `118` tests and exposed one missed pure-`Запись` search case (`1 failed`, `2 warnings`). After the SQL projection covered every visible-title query, the four named PostgreSQL boundaries passed (`4 passed`, `2 warnings` in `8.26s`). Ruff, JavaScript syntax, public-API shape, privacy scrub, and `git diff --check` remained clean.
- The complete §3 isolated feature suite then passed `216 passed`, `2 warnings` in `174.17s`; runner phase passed in `178s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Seventh full PR review correction loop — 2026-07-22

- The next independent complete-diff review found four remaining boundaries: authorization recovery removed the visible upload activity without aborting its in-flight request; the SQL coarse search projection could discard titles whose browser-visible whitespace or filename cleanup differed from storage; removing the final refinement left the previous result count in the accessibility tree; and a measured upload could become processing or failed without announcing the terminal status.
- Manual-upload activities are now tracked until recovery. Session/workspace/access recovery detaches the XHR handlers, aborts every unaccepted request, clears `File`, title, duration, and local-ID references, empties the activity DOM, and only then replaces the host. Accepted uploads also release their private request payload immediately while preserving their safe result link.
- The PostgreSQL candidate projection now mirrors the safe visible-title boundary closely enough to remain a superset: bounded title text, forbidden-metadata fail-closed behavior, authoritative path leaf handling, collapsed browser whitespace, underscore/media-extension cleanup, generated capture/manual-upload fallbacks, and visible duration/time combinations all precede the authoritative Python matcher. Regressions cover `Quarterly   sync`, a cleaned media filename combined with date, and an unsafe stored title projected to neutral `Запись` without echoing it.
- The result live region now announces `Показаны все встречи` when the final refinement disappears instead of retaining `Найдено: N`. Upload progress keeps bounded 10% announcements and additionally announces the row's new compact processing/failure status before dropping its tracked percentage.
- The four named regression boundaries first passed together (`3 passed`, `2 warnings` in `3.53s`; isolated runner `7s`). Ruff, JavaScript syntax, and `git diff --check` passed. The complete §3 isolated feature suite then passed `217 passed`, `2 warnings` in `177.80s`; runner phase passed in `182s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Eighth full PR review correction loop — 2026-07-22

- The next independent complete-diff review reproduced three P2 boundaries: the SQL generated-title predicate was broader and narrower than the Python visible-title contract in different cases; offline/service recovery left persistent live-region text and a queued result-count callback intact; and authorization recovery cleared a manual-upload draft without disabling the still-live upload trigger and page-load CSRF context.
- The PostgreSQL predicate now mirrors the complete generated-title shape, including optional whitespace around the date separator, instead of classifying every `Zoom - …` prefix as neutral. Regressions prove that `Zoom - quarterly sync 14 июл` finds the meaningful visible title while `Zoom-2026-07-14 13:00` remains discoverable through its neutral visible `Запись 14 июл` projection.
- A shared announcement reset invalidates pending count callbacks, clears both persistent announcers, and drops upload progress buckets for offline and service recovery as well as authorization loss. Transient recovery retains selection/history and manual-upload custody; only authorization recovery performs the stronger metadata scrub.
- Session/workspace/access recovery now marks the manual-upload dialog unavailable, aborts and scrubs its tracked requests, disables every surviving upload trigger, and makes readiness depend on the current authorization flag as well as file, duration, and CSRF inputs.
- The four named regressions passed (`4 passed`, `2 warnings` in `3.72s`), and the strengthened localized static contracts passed (`2 passed`, `2 warnings` in `0.04s`). Ruff, JavaScript syntax, and `git diff --check` passed. The complete §3 isolated feature suite then passed `217 passed`, `2 warnings` in `177.14s`; runner phase passed in `181s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Ninth full PR review correction loop — 2026-07-22

- The next independent complete-diff review reproduced five P2 boundaries: the SQL manual-upload predicate classified meaningful prefixed titles as generated; its unsafe-domain alternative omitted the canonical word boundary; an unfiltered truncated refresh announced every meeting as visible; measured upload tracking ended during active unmeasured finalization; and repeated calendar-choice links had identical accessible names.
- The PostgreSQL projection now uses the same complete generated manual-upload shape as the Python projection and the PostgreSQL beginning-of-word boundary for domain-like paths. Regressions preserve combined title/date search for `manual-upload-project planning` and `project_foo.com/path` while the authoritative Python matcher remains the final decision.
- Every rendered list fragment now exposes metadata-only completeness truth. The result live region says `Показаны все встречи` only after the last refinement disappears and the server confirms that the list is not truncated; unfiltered sort/upload/deletion refreshes cannot make that claim from a bounded first page.
- Upload announcement tracking survives the active `Отправляем` state without a trustworthy percentage, so the next processing or failure state is still announced. Calendar-choice links retain the visible `Выбрать встречу` copy and add the row's safe title plus trusted time to their accessible names.
- The five named regressions passed on disposable PostgreSQL (`5 passed`, `2 warnings` in `5.91s`; runner phase `9s`) together with Ruff, JavaScript syntax, and `git diff --check`. The complete §3 isolated feature suite then passed `217 passed`, `2 warnings` in `176.65s`; runner phase passed in `181s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Tenth full PR review correction loop — 2026-07-22

- The next independent complete-diff review reproduced a search false negative for the safe filename edge `__.wav`: the row rendered as `Загруженная запись`, while the SQL coarse candidate projection discarded the same visible query before the authoritative Python matcher. The same review trace exposed two compatibility boundaries: an upload that started without a measurable percentage was not registered for its later terminal announcement, and global sort normalization changed the pre-feature public-API fallback for unknown values.
- The PostgreSQL projection now applies the exact empty-cleaned-filename fallback used by the safe visible title. A synthetic regression proves that `Загруженная запись 14 июл` finds `__.wav` without exposing the stored filename.
- Upload announcement tracking now registers an active compact `uploading` row even when no percentage exists, preserving the next processing or failure announcement. Sort normalization accepts an explicit caller fallback: browser and embedded routes keep `started_desc`, while the unchanged public API keeps `updated_desc` for missing or unknown sort values.
- The four named targeted regressions passed on disposable PostgreSQL (`4 passed`, `2 warnings` in `7.81s`; runner phase `11s`). Ruff, JavaScript syntax, and `git diff --check` passed. The complete §3 isolated feature suite then passed `217 passed`, `2 warnings` in `174.91s`; runner phase passed in `179s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Eleventh full PR review correction loop — 2026-07-22

- The next independent complete-diff review found six remaining boundaries: terminal meeting states had changed public list/detail API semantics; a polling response could arrive after user interaction and replace focused or modal state; authorization recovery retained deletion-row and focus references; removing the final refinement from a truncated collection produced no announcement; measured-to-unmeasured and normal upload completion left stale progress text; and the search placeholder differed from the approved exact copy.
- `ABORTED` and `EXPIRED` now retain their pre-feature public `submitted` status, exact API-filter membership, and detail processing state. A private non-serialized meeting-status attribute drives only the browser/embedded compact failure projection and grouped web filter, with ID-level list/detail regressions proving the API boundary.
- Both the start and the pre-swap edge of an HTMX progress poll now check active focus, hover, selection, and modal interaction. A late response is canceled before DOM replacement. Authorization recovery closes deletion without restoring stale focus and clears pending row, form, and fallback references before replacing private list metadata.
- Removing the final refinement announces either `Показаны все встречи` for a complete response or `Показана первая часть встреч без поиска и фильтров` for a truncated response. Upload announcements cover measured-to-unmeasured continuation and silent normal completion, and always clear stale percentage text without restoring a visible ready badge. The search placeholder now exactly matches `Поиск встреч`.
- The pure unit/static correction set passed `97 passed`, `2 warnings` in `0.62s`. The ID-level PostgreSQL public-API/detail/web-projection regression passed independently (`1 passed`, `2 warnings` in `4.18s`; runner phase `7s`). Ruff, JavaScript syntax, and `git diff --check` passed.
- The complete §3 isolated feature suite passed `217 passed`, `2 warnings` in `181.03s`; runner phase passed in `186s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Twelfth full PR review correction loop — 2026-07-22

- The next independent complete-diff review found seven remaining revocation, concurrency, deletion, upload, accessibility, and responsive boundaries: detail playback polling retained private content after authorization loss; a late progress poll could replace a newer refinement; `meeting_not_found` remained retryable; upload refresh used page-load query state; failed or canceled upload rows retained terminal progress; the activity host announced every XHR event; and the narrow layout hid `Снять выбор`.
- Authorization loss during detail polling now replaces the complete private `<main>`, resets the document title and URL to the neutral list route, clears HTMX history state, and focuses a labelled recovery heading/action. A real-JavaScript Node regression proves that private title and revision metadata leave the connected DOM on an unknown fail-closed `403`; a disconnected stale detail response is ignored.
- Meeting-list requests now carry monotonic generations. Progress polls are blocked during authoritative work and their late swaps/errors are ignored after interaction or refinement; an older search/filter/sort response also cannot overtake a newer one. A real-JavaScript regression executes the production asset and proves both stale-poll and stale-refinement rejection while allowing the newest response.
- A `404 meeting_not_found` deletion removes and scrubs the stale row without offering retry. Successful upload refreshes serialize the current filter form rather than a page-load URL. Manual upload shows at most `99%` until server acceptance, hides and clears progress for every terminal state, and sends VoiceOver only state changes plus bounded 10% announcements through a dedicated atomic live region.
- The selection toolbar wraps instead of hiding `Снять выбор` below `620px`, preserving the keyboard and VoiceOver escape from batch selection.
- The pure changed-surface set passed `156 passed`, `2 warnings` in `0.56s`; Ruff, JavaScript syntax, and `git diff --check` passed. The complete §3 isolated feature suite passed `219 passed`, `2 warnings` in `139.88s`; runner phase passed in `143s` and removed its disposable PostgreSQL container. The §4 calendar/playback/deletion/access compatibility suite then passed `78 passed`, `2 warnings` in `106.55s`; runner phase passed in `110s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Thirteenth full PR review correction loop — 2026-07-22

- The next complete-diff review reproduced three remaining consistency and privacy boundaries: a stale polling `401`/`403` could be ignored before fail-closed recovery; terminal upload sessions rendered as failures but remained outside the grouped web `Требуют внимания` filter; and passive hover, retained focus, or selection could pause one-second progress polling indefinitely.
- Authorization loss now bypasses stale-request and interaction suppression at both the pre-swap and error boundaries. Real production-JavaScript regressions execute stale polling `401` and `403` events and prove that private list text is replaced by the bounded session/access recovery and the URL is neutralized.
- Terminal `failed`, `aborted`, and `expired` upload sessions now use the same private presentation status for compact copy and grouped web filtering. A PostgreSQL regression proves that the row appears under `Требуют внимания` while exact public `uploading`/`failed` filters and serialized status remain unchanged. Deletion continues to outrank upload failure.
- Passive hover, keyboard focus, and surviving selection no longer block current progress responses. Only an open list-related modal pauses replacement; generation checks still reject polling started before a newer search/filter/sort request, and existing reconciliation preserves surviving selection and focus after an accepted swap.
- The first named PostgreSQL run exposed only an over-broad negative assertion because the synthetic title correctly remained in the search input; the assertion was narrowed to the meeting row ID and then passed (`1 passed`, `2 warnings` in `3.04s`; runner phase `6s`). The pure unit/static set passed `100 passed`, `2 warnings` in `0.34s`. Ruff, JavaScript syntax, and `git diff --check` passed.
- The complete §3 isolated feature suite passed `225 passed`, `2 warnings` in `172.75s`; runner phase passed in `176s` and removed its disposable PostgreSQL container. The §4 calendar/playback/deletion/access compatibility suite passed `78 passed`, `2 warnings` in `150.79s`; runner phase passed in `155s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Fourteenth full PR review correction loop — 2026-07-22

- An independent complete-diff review found eight remaining boundaries: forbidden `replaceState` could leave a private URL visible; terminal projected failures could poll forever; accepted polling could discard focused row controls; same-form refinements lacked explicit HTMX replacement ordering; deletion refresh could override newer user focus; the public API echoed a normalized unknown sort; a focusable non-action row duplicated the nested primary link; and deletion feedback could be announced by nested live regions.
- Fail-closed recovery now navigates to the neutral list route when `history.replaceState` is unavailable. Terminal private failure projection stops polling. Accepted progress swaps restore the same native control or a bounded fallback, but both polling and deletion refresh respect a newer user focus choice. Real production-JavaScript regressions exercise the polling and delayed-refresh branches.
- Search/filter/sort requests use `hx-sync="this:replace"`, so a newer refinement aborts and replaces an older request before swap. Browser/embedded routes normalize unknown sort to `started_desc`; the public API preserves its previous internal `updated_desc` fallback and requested response value.
- The `li` is now a non-focusable semantic list item. One native link owns opening and its complete description; native checkbox `Space` owns selection; native delete/calendar controls retain their own names. Visually quiet controls remain in the tab/accessibility sequence and reveal via `focus-within`, eliminating custom row keyboard code and duplicate metadata announcements.
- One persistent polite/atomic deletion region owns announcements; nested server/client fragments no longer declare another live region. Post-delete fallback targets the next/previous primary link and is skipped if the user has already focused another connected control.
- The pure unit/static set passed `162 passed`, `2 warnings` in `0.65s`; two focused production-JavaScript runtime regressions passed, and the API-sort/browser-sort/deletion PostgreSQL set passed `6 passed`, `2 warnings` in `24.68s` (runner phase `29s`, isolated container removed). Ruff, JavaScript syntax, and `git diff --check` passed.
- The first complete §3 rerun exposed one obsolete source-shape assertion after URL neutralization moved into the shared helper; the privacy behavior itself remained covered. After updating that assertion, the complete §3 isolated feature suite passed `227 passed`, `2 warnings` in `181.90s`; runner phase passed in `187s` and removed its disposable PostgreSQL container. The §4 calendar/playback/deletion/access compatibility suite passed `78 passed`, `2 warnings` in `137.54s`; runner phase passed in `142s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Fifteenth full PR review correction loop — 2026-07-22

- The next independent complete-diff review found ten remaining privacy, projection, URL, focus, announcement, and accessibility boundaries. Ready meeting details retained private content after authorization failures outside active playback polling; accepted upload extensions drifted across UI, visible title, and SQL search; internal API filter values could produce a concealed web filter; automatic list replacements and retry completion could lose or steal focus; batch deletion emitted repeated/stale live messages; dynamic revocation copy diverged from the static privacy boundary; background refreshes reannounced result counts; and the disabled upload accessible name dropped its visible label.
- Detail authorization recovery now covers ready and preparing pages across HTMX actions, speaker-name save, export, and playback fetches. `401`, `403`, `404`, `410`, or a redirected login replace the complete private main, neutralize history/title/URL, and use the indistinguishable `Встреча больше недоступна` copy. Real production-JavaScript regressions prove both polling and non-polling detail removal.
- One shared media-filename module owns every accepted extension, MIME accept string, path leaf, extension predicate, and visible filename cleanup. Manual ingestion, Python projection, HTML input, and PostgreSQL search now agree for `.wave`, `.rf64`, `.w64`, `.adts`, `.oga`, `.opus`, `.mka`, and the existing formats; synthetic path tests prove that legacy local directories never reach the visible title.
- Browser and embedded routes accept only the status/access literals their controls can display, while the public API retains its larger exact vocabulary. Automatic polling, accepted-upload refresh, recovery, and status-transition replacement snapshot the latest row/toolbar/retry focus and restore only while the user still owns that surface; moving to another row or search is respected. Result counts announce only intentional search/status/access refinements.
- Batch deletion clears stale feedback before work, validates every bounded server response without mutating the live region inside the request loop, and publishes exactly one final success or failure message. The retry error remains visible in the dialog but no longer competes as a second live region. Authorization-disabled upload copy keeps `Загрузить запись` in its accessible name.
- The pure unit/static regression set passed `172 passed`, `2 warnings` in `0.97s`; the new filename/search and hidden-filter PostgreSQL regressions passed `2 passed`, `2 warnings` in `7.38s` (runner phase `10s`). Ruff, JavaScript syntax, and `git diff --check` passed.
- The complete §3 isolated feature suite passed `237 passed`, `2 warnings` in `190.58s`; runner phase passed in `195s` and removed its disposable PostgreSQL container. The §4 calendar/playback/deletion/access compatibility suite passed `78 passed`, `2 warnings` in `138.00s`; runner phase passed in `142s` and removed its disposable PostgreSQL container. The same two documented dependency warnings remained; no private data, production access, native change, release, or deploy was introduced.

### Sixteenth full PR review correction loop — 2026-07-22

- The next independent complete-diff review found six remaining compatibility and interaction boundaries: the successful speaker-name `303` redirect was mistaken for session loss; action-scoped `speaker_not_found` and `export_policy_denied` errors removed an otherwise accessible detail; expanded filename cleanup changed public list/detail titles; active uploads were absent from the visible `В обработке` filter and legacy status URLs failed validation; a later automatic request could discard a pending refinement announcement; and the reset action performed a full navigation, reset sorting, and skipped focus/live feedback.
- Detail fetch recovery now treats only a redirect whose final path is `/login` as session loss. Canonical action-scoped problem codes remain local to the speaker/export control, while unknown `401`/`403` and meeting-level `404`/`410` responses remain fail-closed. Production-JavaScript regressions execute the same-detail redirect, local `404`/`403` errors, and retained private-detail boundary.
- Browser/embedded title presentation and search continue to clean every accepted media extension without exposing a local path. Public list/detail serialization retains the pre-feature extension-cleanup set and exact title sort/search payload contract; PostgreSQL regressions prove `.wave` remains serialized while its web row is clean.
- `В обработке` now includes local custody, active upload, submitted, and processing states. Existing web URLs containing `local_only`, `uploading`, `submitted`, `blocked`, or `unavailable` normalize into one of the four visible status groups; unknown status and hidden access values still fail validation.
- Pending result-count intent survives a newer authoritative request until the winning response swaps. `Сбросить` clears query/status/access through the synchronized HTMX form, preserves the selected sort and no-JavaScript fallback URL, updates its visible state, announces the authoritative result, and restores focus to `Мои встречи`.
- The pure unit/static regression set passed `177 passed`, `2 warnings` in `1.08s`. The targeted public-title/status/upload PostgreSQL set passed `38 passed`, `2 warnings` in `85.15s`; runner phase passed in `89s` and removed its disposable container. Ruff, JavaScript syntax, and `git diff --check` passed.
- The complete §3 isolated feature suite passed `242 passed`, `2 warnings` in `180.08s`; runner phase passed in `184s` and removed its disposable PostgreSQL container. The §4 calendar/playback/deletion/access compatibility suite passed `78 passed`, `2 warnings` in `132.03s`; runner phase passed in `136s` and removed its disposable container. The same two documented dependency warnings remained; no feature-owned warning, private data, production access, native change, release, or deploy was introduced.

### Seventeenth full review and released-master synchronization — 2026-07-22

- The next independent complete-diff review exposed that released Feature 121 had landed on `origin/master` while Feature 122 was still under review. The review transport failed during remote compaction before it could produce a final verdict, so this run is not treated as a clean review result; its integration warning was handled before any push or release.
- Feature 122 was merged with `origin/master` at `478c8832`. Conflict resolution preserved both sides: Feature 121 summary/workflow/sharing dialogs, metadata-only same-tab candidate recovery, and modal focus containment remain present, while Feature 122 list polling, privacy recovery, deletion feedback, upload custody, result announcements, and refinement/focus rules remain authoritative for the list.
- The merge exposed three silent compatibility losses that text conflict markers did not cover: `date_label`, `sort_label`, and the shared icon adapter had disappeared from auto-merged modules. They were restored with their released signatures, and the combined static privacy contract now permits only the metadata-only candidate state alongside explicit private HTMX-history clearing.
- The combined pure unit/rendering/static/accessibility set passed `182 passed`, `2 warnings` in `1.87s`. The complete §3 isolated feature suite passed `243 passed`, `2 warnings` in `256.55s`; the §4 calendar/playback/deletion/access compatibility suite passed `80 passed`, `2 warnings` in `148.68s`. Both disposable PostgreSQL containers were removed. The warning pair remains the documented fixture-rewrite and Starlette/httpx deprecation only.
- JavaScript syntax, Python compilation, conflict-marker audit, and `git diff --check` passed. No private data or new feature-owned native change was introduced; the native files present in the merge are the already released Feature 121 baseline and will be validated again by the full repository gate.

### Eighteenth scoped review correction loop — 2026-07-23

- The backend/data-contract review completed with the exact `NO_FINDINGS` verdict after inspecting the Feature 122 schema, query, projection, upload, route, and regression-test diff against the released master baseline.
- Its independent lint probe exposed one integration-only formatting defect: adding the two private Pydantic presentation attributes had removed the blank line between third-party and first-party imports in `api/schemas.py`. The import boundary was restored without changing runtime behavior or the serialized public API.
- The focused Ruff check passed, the pure view-model/web-shell suite passed `142 passed`, `2 warnings` in `0.21s`, and `git diff --check` passed. The warnings remain the documented fixture-rewrite and Starlette/httpx deprecation only; no private data, production access, native change, release, or deploy was introduced.

### Nineteenth backend/data review correction loop — 2026-07-23

- The required backend/data-contract repeat on the lint-corrected HEAD found one P2 search-projection mismatch: a non-authoritative stored title equal to `Запись без названия` renders as the neutral visible title `Запись`, but the PostgreSQL coarse projection retained the longer stored value and could discard a combined visible query such as `Запись 1 мин 14 июл` before the authoritative Python matcher.
- A synthetic PostgreSQL regression reproduced the false negative (`1 failed`, `2 warnings` in `3.55s`; isolated container removed). The SQL projection now applies the same non-authoritative fallback-title rule as `meeting_list_title()` while preserving authoritative user/calendar/upload-provided titles unchanged.
- The named regression then passed (`1 passed`, `2 warnings` in `3.52s`; isolated container removed). The complete §3 isolated feature suite passed `243 passed`, `2 warnings` in `161.93s`; runner phase passed in `166s` and removed its disposable PostgreSQL container. Focused Ruff, JavaScript syntax, and `git diff --check` also passed. The warning pair remains the documented fixture-rewrite and Starlette/httpx deprecation only; no private data, production access, native change, release, or deploy was introduced.

### Twentieth JS review correction loop — 2026-07-23

- The independent client review found four interaction boundaries: authorization recovery did not invalidate newer in-flight list responses; a `401`/`403` from a poll whose source had been detached could miss the body listener; polling could restore a selected-row link instead of the still-connected selection toolbar; and a completed upload disappearing under a processing filter produced no live announcement.
- Authorization recovery now advances the list request generation before scrubbing private metadata, and each list XHR observes detached-source `readystatechange` failures so session/workspace/access recovery remains fail-closed even when HTMX cannot bubble `htmx:responseError`. Duplicate recovery for one request is ignored. Toolbar focus snapshots retain the exact batch control, while upload progress keeps the last safe visible title until a terminal row returns and provides evidence for its completion status.
- Production-JavaScript regressions cover the generation invalidation, detached poll recovery, toolbar focus preservation, and filtered upload completion announcement. The complete cabinet static/runtime contract passed `37 passed`, `2 warnings` in `0.64s`; JavaScript syntax and `git diff --check` passed. The warning pair remains the documented fixture-rewrite and Starlette/httpx deprecation only.

### Twenty-first JS review correction loop — 2026-07-23

- The repeat client review found one P2 truthfulness defect: a row disappearing after a search/filter/sort change was not evidence of successful upload completion, so the new live announcement could falsely report success for an active, failed, or canceled upload.
- Missing rows now retain their safe progress metadata without announcing success. The completion announcement is emitted only when a later visible row supplies a terminal status; authorization cleanup still clears the retained metadata. The runtime regression covers both the filtered disappearance and the terminal row returning.
- The follow-up review found a bounded-state gap in that retention path. Upload metadata and progress buckets now carry a five-minute last-seen TTL and are pruned on each poll, so a permanently filtered-out row cannot retain private title metadata indefinitely; the runtime harness covers orphan eviction.
- The next review noted that polling can stop as soon as a filter removes every active row. Cleanup is now independently scheduled from the first retained progress state, re-schedules while tracked metadata remains, and is canceled by authorization scrubbing; the regression invokes the timer without a follow-up poll.
- The cumulative client review then found no concrete regressions in authorization recovery, stale-request handling, focus restoration, live announcements, data exposure, state lifetime, or timer cleanup. The focused cabinet contract suite passed `37 passed`, `2 warnings`; JavaScript syntax and `git diff --check` also passed.

### Full repository gate correction loop — 2026-07-23

- The first full `infra/scripts/ci-local.sh` run reached the server parallel phase and passed `2266` tests, but exposed one stale contract assertion: the unavailable-meeting copy had already changed to the Feature 122 wording `Встреча больше недоступна` while the review test still expected the released baseline text `Страница недоступна`.
- The contract now asserts the current generic unavailable-state copy without changing runtime behavior or exposing meeting data. The isolated correction test passed `3 passed`, `2 warnings` in `11.72s`; the warning pair remains the documented fixture-rewrite and Starlette/httpx deprecation only.
- The rerun of the complete repository gate passed macOS legacy-architecture guard, Swift build and `608` Swift tests, `ContractValidation`, server parallel `2267 passed, 1 skipped`, strict PostgreSQL `41 passed, 1 skipped`, Ruff, Python compilation, Compose validation, deployment evidence scan, and finished with `ci_local_result=pass`; the existing fixture-rewrite, Starlette/httpx, and SQLAlchemy cycle warnings remained documented only.

### Ponytail final review loop — 2026-07-23

- The first full Ponytail pass proposed removing the bounded SQL visible-row coarse projection and consolidating the independent Node/FakeElement production-JavaScript harnesses. Both were rejected as intentional: the SQL projection prevents per-meeting access/media queries before the authoritative Python matcher, while the harnesses cover separate DOM surfaces without adding a test dependency.
- Follow-up passes removed the unused upload refresh override, the single-entry session-code set, duplicate detail-recovery copy, and unused meeting-title DOM id. The required final Ponytail review of the post-`c6927c6c` tree returned exactly `Lean already. Ship.`; no unjustified complexity remains.

### Spec Kit analysis correction loop — 2026-07-23

- The first post-Ponytail `$speckit-analyze` pass found one accessibility wording conflict, two recovery states missing from the formal data/evidence trace, one missing explicit `FR-001` task tag, and one terminology mismatch. The UX checklist now keeps contextual controls in the tab order and accessibility tree, while the data model, evidence matrix, recovery tasks, and synthetic quickstart explicitly distinguish workspace reselection from access denial and their different actions.
- The corrected read-only `$speckit-checklist` audit is clean at `60/60` UX items with `0` critical/high/medium gaps. The corrected `$speckit-analyze` rerun is clean at `0` critical, `0` high, `0` medium, and `0` low findings: `36/36` functional requirements, `12/12` success criteria, `38/38` mapped completed tasks, `76/76` checklist items, `0` unmapped tasks, and `0` unresolved placeholders. No implementation behavior or private evidence is changed by this documentation-only repair.

### Final Arc correction loop — 2026-07-23

- The complete-diff Arc-review found two actionable boundaries: summary/share mutations could leave a revoked private detail page in the DOM, and an invalid browser sort could remain in the address bar and polling URL after visual normalization.
- Summary candidate mutation, polling, and resolution now share the same fail-closed detail recovery as playback/export; recipient search, grants, and invitations use the same recovery wrapper while preserving local action problem codes. A recovery marker prevents follow-up error copy from reintroducing stale private content.
- Browser and embedded list routes now redirect direct invalid `sort` values to a canonical `started_desc` URL. HTMX responses set `HX-Replace-Url` and render polling links with the canonical query, preserving other filters and dropping duplicate sort parameters.
- The focused static/runtime contract passed `37 passed`, `2 warnings`; Ruff, JavaScript syntax, and `git diff --check` passed. The direct integration probe is intentionally blocked without `TWOBRAIN_DATABASE_URL`; the canonical full CI runner remains the required PostgreSQL evidence.

### Final Arc correction loop — 2026-07-23 (second pass)

- The final complete-diff Arc-review found two P2 boundaries: a stale share-fragment `404 meeting_not_found` could replace an otherwise accessible detail page, and legacy grouped status filters could remain in the browser address and polling URL after visual normalization.
- Share-fragment errors are now identified from the triggering share control/host, prevented from swapping the detail, and rendered as a local accessible error inside the detail. Share fetch actions also treat `meeting_not_found` as an action-local code; true session, workspace, and access-loss responses still use fail-closed detail recovery.
- Browser and embedded list routes now canonicalize legacy `status` values (`uploading`, `submitted`, `local_only` → `processing`; `blocked`, `unavailable` → `failed`) in direct redirects and HTMX `HX-Replace-Url`/polling links while preserving the other query parameters.
- The focused static/runtime contract passed `38 passed`, `2 warnings`; the web-shell unit suite passed `62 passed`, `2 warnings`; Ruff, JavaScript syntax, and `git diff --check` passed. The database-backed canonical-status regression is included in the next full CI run; a direct invocation remains blocked without `TWOBRAIN_DATABASE_URL`.

### Full repository gate correction loop — 2026-07-23 (canonical-status regression)

- The first rerun exposed only a stale test fixture: `q=Запись` did not match the seeded processing meeting, and the HTMX fragment does not render the full filter form. The regression now uses the seeded `Планирование релиза` row, verifies the direct canonical page's selected status, and checks the canonical polling URL in the fragment.
- The focused isolated PostgreSQL regression passed `1 passed`, `2 warnings` in `7.10s`; the disposable container was removed. The full `infra/scripts/ci-local.sh` rerun finished with `ci_local_result=pass`: macOS legacy-architecture guard, Swift build, `608` Swift tests, `ContractValidation`, PostgreSQL suites, Ruff, Python compilation, Compose validation, and deployment-evidence scan all passed. The existing fixture-rewrite, Starlette/httpx, and SQLAlchemy-cycle warnings remained documented only.
