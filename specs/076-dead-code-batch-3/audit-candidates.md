# Audit Candidates: Dead Code Batch 3

## Baseline

Fresh `origin/master` baseline: `4750faef` after PR #2593.

Swift tracked source/test LOC before deletion: 53,319.

Swift tracked source/test LOC after deletion: 53,315 (`-4`).

## Scanner Evidence

Commands:

```sh
rg -n "^\\s*private\\s+(func|var|let)\\s+[A-Za-z_][A-Za-z0-9_]*" apps/macos --glob '*.swift'
rg -n "^def _[A-Za-z0-9_]+\\(|^async def _[A-Za-z0-9_]+\\(|^class _[A-Za-z0-9_]+" apps/server/src apps/server/tests --glob '*.py'
rg -n "^[A-Za-z_][A-Za-z0-9_]*\\(\\) \\{" infra scripts --glob '*.sh'
```

Result: no direct one-reference private helper/function candidates remained
after 074 and 075.

## `delete now`

### `BluetoothRouteMonitor.Foundation`

- Path: `apps/macos/RecApp/Sources/AudioHealth/BluetoothRouteMonitor.swift`
- Evidence: the file uses `TwoBrainRecShared` models and Swift standard library
  constructs only; `swift build --package-path apps/macos` passes without the
  import.
- Risk surface: audio health evidence wrapper.
- Validation: Swift build plus Bluetooth/route focused tests.

### `VolumeMuteMapper.Foundation`

- Path: `apps/macos/RecApp/Sources/AudioSetup/VolumeMuteMapper.swift`
- Evidence: the file uses standard-library `Codable`, `Equatable`, `Sendable`,
  and `Double`; `swift build --package-path apps/macos` passes without the
  import.
- Risk surface: volume/mute mapping model.
- Validation: Swift build plus volume mute focused tests.

### `CaptureControlView.AppKit`

- Path: `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- Evidence: the file compiles with `SwiftUI` and `TwoBrainRecShared`; the
  direct AppKit import is not required after PR #2590/#2591.
- Risk surface: visible capture control UI.
- Validation: Swift build plus capture control focused tests.

## `keep intentionally`

### `ExperimentalPassthroughCoordinator.Foundation`

- Path: `apps/macos/RecApp/Sources/Capture/ExperimentalPassthroughCoordinator.swift`
- Evidence: removing the import fails compile with missing `ObservableObject`
  and `@Published`.
- Classification: `keep intentionally`.
- Future path: consider a separate import-normalization slice if replacing with
  a narrower framework import is desired.

## Deferred

- XCTest class names and command-line tool entry-point types: keep
  intentionally because they are compiler/test discovery contracts.
- Large SwiftUI file splits: separate slice only, with product/UI validation.
