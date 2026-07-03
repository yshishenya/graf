# Audit Candidates: Dead Code Batch 4

## Baseline

Fresh `origin/master` baseline: `8ee722ce` after PR #2603.

Swift tracked source/test LOC before deletion: 53,315.

Swift tracked source/test LOC after deletion: 53,304 (`-11`).

## Scanner Evidence

Commands:

```sh
rg -n "^import (Foundation|AppKit|AVFoundation|Combine|CoreAudio|CoreGraphics|AudioToolbox|SwiftUI|TwoBrainRecShared)$" apps/macos --glob '*.swift'
rg -n "^\\s*private\\s+(func|var|let)\\s+[A-Za-z_][A-Za-z0-9_]*" apps/macos --glob '*.swift'
python3 - <<'PY'
# Static import-token screen for files with Foundation imports but without
# obvious Foundation symbols. Compile remains the deciding evidence.
PY
```

Result: no broad helper deletion target is safer than another small import-only
batch. Static import-token screening identified production/shared files whose
body appears to use Swift standard library and project models only.

## `delete now`

- `apps/macos/RecApp/Sources/AudioHealth/BluetoothRoutePolicy.swift`:
  `Foundation`
- `apps/macos/RecApp/Sources/AudioSetup/GuidedDeviceManagementService.swift`:
  `Foundation`
- `apps/macos/RecApp/Sources/AudioSetup/PhysicalDeviceSelectionViewModel.swift`:
  `Foundation`
- `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`:
  `Foundation`
- `apps/macos/RecApp/Sources/Capture/RecordingRouteMetadataService.swift`:
  `Foundation`
- `apps/macos/Shared/Sources/Models/AudioStates.swift`: `Foundation`
- `apps/macos/Shared/Sources/Models/RecordingTimelineEvidence.swift`:
  `Foundation`
- `apps/macos/Shared/Sources/Routing/LiveRouteClientActivity.swift`:
  `Foundation`

Evidence: `swift build --package-path apps/macos` passes after removing all
eight imports. Focused validation for touched surfaces passes with 28 tests and
0 failures.

## `keep intentionally`

- `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`: uses
  `CharacterSet` through `trimmingCharacters(in:)`.
- `apps/macos/Shared/Sources/Models/PlatformSupport.swift`: uses
  `OperatingSystemVersion` and `ProcessInfo`.
- `apps/macos/RecApp/Sources/Capture/ExperimentalPassthroughCoordinator.swift`:
  previously compile-probed in 076; `ObservableObject` and `@Published` require
  an import contract.

## Deferred

- Test-only imports with ambiguous XCTest/Foundation relationships.
- Replacing `Foundation` with narrower modules.
- Large SwiftUI file splits and runtime refactors.
