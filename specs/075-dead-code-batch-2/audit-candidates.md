# Audit Candidates: Dead Code Batch 2

## Baseline

Runtime LOC baseline from 2026-07-01 fresh `origin/master`
(`d43aa049`, after PR #2589):

- Python: 35,823
- Swift tracked source/tests: 53,339

After deletion, tracked Swift source/tests: 53,319 (`-20`).

## Candidates

Evidence command:

```sh
rg -n "statusChip\\(" apps/macos apps/server/src apps/server/tests infra scripts
rg -n "waitUntil\\(" apps/macos apps/server/src apps/server/tests infra scripts
```

### `delete now`: `DesktopMeetingShellView.statusChip`

- Path: `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- Evidence: the only match is the private function definition.
- Risk surface: desktop cabinet shell UI. The helper is not wired into the view
  tree.
- Validation: Swift focused tests/build for shared desktop/capture surfaces.

### `delete now`: `LivePassthroughPolicyTests.waitUntil`

- Path: `apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift`
- Evidence: the only match is the private test helper definition.
- Risk surface: test-only helper.
- Validation: Swift focused tests for live passthrough policy.

## Kept Intentionally

- Other `private` Swift helpers with active same-file or test references.

## Deferred

- Broad SwiftUI view slimming and large-file cleanup; those need separate
  evidence because SwiftUI references are often local and view-builder based.
