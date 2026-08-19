# Quickstart: Пострелизная очистка интерфейса

## Focused server checks

```sh
cd apps/server
uv run pytest -q \
  tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_settings_ui_contract.py \
  tests/unit/test_cabinet_web_shell.py \
  -k 'sidebar or rail or settings or tooltip'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd ../..
git diff --check
```

Run the existing isolated PostgreSQL settings matrix once after template changes:

```sh
apps/server/scripts/run_local_postgres_tests.sh \
  tests/contract/test_settings_ui_contract.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_settings_ia_flow.py \
  tests/integration/test_cabinet_meeting_list.py \
  -k 'settings or sidebar or cabinet_settings_calendar_anchor'
```

## Focused macOS checks

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'AppControlAccessibilityTests|DesktopMeetingShellWebViewBoundaryTests'
swift build --package-path apps/macos
```

## Computed Browser matrix

For widths `640, 720, 980, 981, 1120, 1121, 1280` inspect standalone `/settings` and embedded `/desktop/settings` after shell initialization.

For each state record metadata-only values:

- sidebar width `64` compact / `176` expanded;
- toggle, selected navigation and profile boxes `40×40` compact;
- profile computed `display != none`, `visibility = visible`, `opacity > 0`;
- control center difference ≤1px;
- `document.documentElement.scrollWidth === document.documentElement.clientWidth`;
- two activations at the same toggle coordinate restore the original state.

Visit overview, one regular form, calendar and billing. Require one navigation landmark, one active settings link, one content column and unchanged fragment root.

## GRAF Dev visual matrix

1. Open embedded settings at normal and constrained window sizes.
2. Check profile visibility and menu in compact state.
3. Toggle web sidebar twice without moving the pointer.
4. Toggle native inspector twice without moving the pointer.
5. Require native inspector toggle to remain top-trailing in both states; no overlap with titlebar, recording controls, web sidebar or content.
6. Keyboard through both toggles and profile; require visible focus and correct accessible labels/help.

Screenshots stay outside git and contain no private meeting data or credentials.

## Review and repository gate

Run correctness/root-cause, frontend UX/accessibility, clean-room and Ponytail review. Resolve actionable findings, then run once:

```sh
infra/scripts/ci-local.sh --fast
```

Full CI, deployment, notarization and release publication are outside Feature 174 and remain release-train gates.

## Validation evidence — 2026-08-19

### Pre-change baseline

- Current branch server ran on loopback with the existing synthetic local owner; no production data or private meeting content was used.
- In-app Browser at embedded `720×720`, compact state: sidebar `64×720`, toggle and first navigation target `40×40` at `x=11.5`, horizontal overflow `0`, one navigation landmark and one active settings link.
- The profile trigger rendered `0×0`; parent `.sidebar-foot` computed to `display:none` and `0×0`. This reproduces the user-reachable regression while the child itself still reports `display:flex`, proving that a child-only visibility assertion is insufficient.
- Pre-change focused server selection: `38 passed, 111 deselected`, two existing dependency warnings. The passing source-contract suite did not detect the rendered defect.

### Sidebar cleanup

- Focused sidebar/rail/tooltip selection: `15 passed, 113 deselected`, with the same two existing dependency warnings.
- `node --check` for `cabinet.js` and `git diff --check`: passed.
- Fresh local server instance used the updated static hash `3bb47968eaf1`; this avoided the stale pre-change stylesheet cached by the first dev-server process.
- In-app Browser matrix at `640`, `720`, `980`, `981`, `1120`, `1121`, and `1280`: compact rail `64px`, expanded rail `176px`; compact toggle, selected navigation and profile `40×40`; footer visible as grid; profile visible; no horizontal overflow; one navigation landmark and one active link.
- Toggle center delta between compact and expanded states was `0.5px` at every width. Two clicks at the unchanged `(32, 28)` coordinate restored the original state.

### Native inspector cleanup

- Focused `AppControlAccessibilityTests|DesktopMeetingShellWebViewBoundaryTests`: `36` tests, `0` failures.
- `swift build --package-path apps/macos`: passed (`Build complete`).
- Scoped `git diff --check`: passed.
- Source review confirmed that only the unused `GeometryReader` wrapper was removed; the `VStack`, full-size top alignment, rail background, vertical scroll and `HStack + Spacer` disclosure hit region remain unchanged.

### Settings navigation cleanup

- Focused contract/unit settings selection after the final CSS correction: `27 passed, 69 deselected`, with two existing dependency warnings.
- Isolated PostgreSQL matrix: `33 passed, 97 deselected`; the isolated container was removed successfully.
- The first fresh Browser check exposed a missed late `.settings-page` redesign owner (`220px 368px`). That duplicate was deleted and an exact source guard now prevents a later two-column owner from returning.
- Final in-app Browser matrix covered overview, recording, calendar and billing in standalone `1280×720` and embedded `720×720`: one navigation landmark, one active link, no legacy navigation, one content column, no horizontal overflow. Standalone content started at `x≈217`; embedded content at `x=82`.
- Calendar kept its `calendar-settings-region` HTMX root and content wrapper; the isolated integration test verifies that fragment responses contain no shell/sidebar.
- Caller search after cleanup found no `settings_navigation.html` import, macro call, `settings_mode` render argument or legacy navigation markup in production source.

### GRAF Dev interaction

- Rebuilt and atomically installed `/Applications/GRAF Dev.app` from this branch with the existing Dev signing identity and loopback-only origin; build, nested signing and final signature verification passed.
- Fresh app showed the accepted expanded web rail and visible profile. The native inspector toggle remained top-trailing in compact and expanded states, with no overlap against titlebar, web sidebar or content.
- Two clicks at the unchanged native screen coordinate restored the expanded state. AX exposed truthful `Показать/Скрыть панель управления` labels and help, the expanded settings control and the scroll area.

### Review follow-up

- Correctness and UX/accessibility review findings were resolved: account
  aliases now expose one primary navigation landmark and a separately labelled
  account link group, each with one current item; the profile popup now uses
  disclosure semantics instead of an incomplete ARIA menu contract.
- Review-focused server selection after those changes: `38 passed, 84
  deselected`; focused Swift tests: `36 passed`.
- Expanded isolated PostgreSQL matrix, including provider-link, billing,
  referrals, account aliases and fair-use surfaces: `42 passed, 97 deselected`;
  the isolated container was removed successfully. The first run found the
  missing `fair_use` analytics inventory policy; the final run passed after a
  dedicated fail-closed financial policy was added.
- Focused analytics, billing-security, fair-use, provider-link and cabinet-shell
  contracts: `105 passed`; only the two existing dependency warnings remained.
- `node --check` for `cabinet.js` and pre-commit `git diff --check`: passed.
- Ponytail review proposed broader wrapper/test deletion. Those deletions were
  not applied because the wrappers still own layout classes and the exact
  regression guards caught defects that broader contracts had missed. No new
  dependency or speculative abstraction was added.
- Independent correctness/privacy re-review of the implementation follow-up
  reported no code findings.

### PR review follow-up

- Restored semantic `aria-current="page"` in the labelled account subsection;
  isolated PostgreSQL account/settings selection: `2 passed, 4 deselected`.
- Profile disclosure now preserves the user's focus on outside-click and
  restores trigger focus only for Escape.
- New production-asset WKWebView checks passed: `2 tests`, covering the exact
  embedded `720px` computed `40×40` profile geometry and real disclosure focus
  behavior.
- Native inspector focused XCTest passed: `35 tests`, covering stable dimensions
  and production runtime accessibility labels/hints without source formatting
  assertions.
- `node --check` and `git diff --check` passed.
- Final PR fast gate passed after the follow-up: legacy-audio guard passed,
  server unit suite `1103 passed`, lint and Python compile passed, and the
  isolated PostgreSQL container was removed; only the two known dependency
  warnings remained.
- Exact-revision Codex Security diff scan `8b13ab9a-4619-4e02-bcb0-861eeb8a85e5`
  covered `2369e654..12f659f8` and completed with no findings. TAC was
  unavailable because the local security helper was not logged in; two
  independent reviews covered all 31 files in that exact range. The later
  `f5d659d0` accessibility/focus follow-up was outside this scan and was covered
  by focused runtime tests plus independent correctness review.

### Final closeout

- Final code commit: `f5d659d0`; subsequent commits changed documentation only.
- The initial implementation passed its fast gate at `3a4ce527`. After the PR
  review changed production code, `infra/scripts/ci-local.sh --fast` was run
  again on the same code tree subsequently committed as `f5d659d0`: legacy-audio
  guard passed, server unit suite `1103 passed`, server lint and Python compile
  passed, and the isolated PostgreSQL container was removed. The only warnings
  were the two known dependency warnings. Changes after `f5d659d0` were
  documentation-only.
- `[Unreleased]` documents the user-visible sidebar, settings, native inspector
  and fair-use fixes. Final documentation-only reconciliation does not alter the
  tested implementation SHA.
- GitHub issues `#5372`–`#5384` received Russian task-specific evidence
  comments and remain open until PR/merge evidence exists.
- The in-app Browser viewport override was reset, temporary Browser tabs were
  closed, and loopback test servers on ports `8084`–`8086` were stopped.
- Final review of `2ddf9b0b` found no runtime defects; its two evidence accuracy
  findings were corrected before merge.
