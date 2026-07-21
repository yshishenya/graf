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

From `apps/server`:

```sh
PYTHONPATH=src uv run --extra dev pytest -q \
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
