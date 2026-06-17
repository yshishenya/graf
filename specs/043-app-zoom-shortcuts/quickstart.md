# Quickstart: App Zoom Shortcuts

## Prerequisites

- macOS development host with Swift 6 toolchain.
- Repository checkout on `043-app-zoom-shortcuts`.
- Optional live cabinet configuration for manual smoke:
  - `TWO_BRAIN_REC_CABINET_BASE_URL`
  - workspace/session headers already supported by the desktop app environment.

## Local Automated Validation

Run focused macOS tests:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'WorkspaceZoom|EmbeddedCabinetWebViewZoom|DesktopCabinetWorkspace'
```

Run existing desktop control regression coverage:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'AppControlAccessibility|CaptureControl|CaptureIndicator'
```

Run the macOS foundation script:

```sh
sh apps/macos/Scripts/validate-foundation.sh
```

Run repository local CI if time permits:

```sh
sh infra/scripts/ci-local.sh
```

## Manual Smoke

1. Build and launch the macOS app from the Swift package.
2. Configure the cabinet URL if needed.
3. Open the meeting workspace.
4. Press Command-Plus or Command-Equals and confirm the embedded workspace grows.
5. Press Command-Minus and confirm the embedded workspace shrinks.
6. Press Command-0 and confirm the embedded workspace returns to 100%.
7. Start a safe local recording only when test permissions and environment are
   appropriate, then confirm the visible indicator and Stop remain reachable
   while changing workspace zoom.

## Expected Results

- Zoom commands affect only the embedded meeting workspace.
- Native recording controls, upload truth, local audio readiness, routes,
  headers, and local recording state remain unchanged.
- Saved supported zoom values restore after relaunch.
- Invalid saved zoom values fall back to 100%.
