# Audit Candidates: Dead Code Batch 5

## Baseline

Fresh `origin/master` baseline: `fe57fd7d` after PR #2614.

Swift tracked source/test LOC before deletion: 53,679.

Swift tracked source/test LOC after deletion: 53,673 (`-6`).

## Scanner Evidence

Commands:

```sh
python3 - <<'PY'
from pathlib import Path
roots=[Path('apps/macos')]
for root in roots:
    total=0
    files=0
    for p in root.rglob('*.swift'):
        files+=1
        total+=sum(1 for _ in p.open(errors='ignore'))
    print(f'{root}: files={files} swift_loc={total}')
PY

python3 - <<'PY'
# Static import-token screen for files with Foundation imports but without
# obvious Foundation symbols. Compile remains the deciding evidence.
PY

rg -n '^import (Foundation|AppKit|AVFoundation|Combine|CoreAudio|AudioToolbox|ScreenCaptureKit|SwiftUI|TwoBrainRecShared)$' apps/macos --glob '*.swift'
```

Result: the source import-token screen identified eight production/shared
files. Manual review narrowed the safe `delete now` set to three source files;
the remaining candidates have hidden or explicit import contracts.

## `delete now`

- `apps/macos/Shared/Sources/Buffering/LocalBufferContracts.swift`:
  `Foundation`
- `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift`: `Foundation`
- `apps/macos/Shared/Sources/Routing/LowResourceRouteTruth.swift`:
  `Foundation`

Evidence: `swift build --package-path apps/macos` passes after removing all
three imports. Focused validation passes with 77 tests and 0 failures:
`LatencyGateTests|LowResourceRouteTruthTests|LowResourceRouteLifecycleTests|DesktopUploadQueueTests|RecordingPrerequisiteGateTests`.

## `keep intentionally`

- `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`: uses
  Foundation string trimming and character-set behavior.
- `apps/macos/RecApp/Sources/Installer/AudioDeviceRestorationService.swift`:
  uses Foundation-provided localized error/string behavior.
- `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`: uses
  Foundation string range options including regular expression and
  case-insensitive matching.
- `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift`: uses Foundation
  string trimming and character-set behavior.

## `risky / needs spec`

- `apps/macos/RecApp/Sources/Capture/ExperimentalPassthroughCoordinator.swift`:
  the import appears to provide the observable-object/property-wrapper compile
  contract. Replacing it with a narrower module would not reduce LOC and should
  wait for a separate import-contract cleanup if still desired.

## Deferred

- Test-only imports with ambiguous XCTest/Foundation relationships.
- Replacing `Foundation` with narrower modules where line count does not
  decrease.
- Large SwiftUI file splits and runtime refactors.
