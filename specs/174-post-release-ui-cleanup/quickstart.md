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
