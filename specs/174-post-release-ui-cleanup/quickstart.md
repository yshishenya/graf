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
