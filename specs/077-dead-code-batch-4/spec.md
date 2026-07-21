# Feature Specification: Dead Code Batch 4

**Feature Branch**: `codex/077-dead-code-batch-4`

**Created**: 2026-07-01

**Status**: Implemented import/dead-code cleanup; no deploy or product behavior change

**Input**: Continue the Ponytail cleanup program after 076 by removing only
compile-proven unused Swift `Foundation` imports from macOS audio, capture, and
shared model files. Do not split files, rewrite runtime flow, or add tooling.

## User Scenarios & Testing

### User Story 1 - Remove Proven Unused Foundation Imports (Priority: P1)

As a product maintainer, I want the next cleanup batch to remove only Swift
`Foundation` imports that compile without the import, so the macOS codebase gets
smaller without changing product behavior.

**Why this priority**: The previous helper scans found no safer zero-reference
helper targets. Import-only deletion is the smallest safe improvement that still
reduces code surface in audio/capture-related files.

**Independent Test**: The batch is independently testable by compiling the
macOS package and running focused tests for touched audio, capture, route, and
shared model surfaces.

**Acceptance Scenarios**:

1. **Given** a fresh checkout from `origin/master`, **When** selected
   `Foundation` imports are removed, **Then** `swift build --package-path
   apps/macos` succeeds.
2. **Given** the import-only deletion diff, **When** focused Swift validation
   runs for touched surfaces, **Then** tests pass with no behavior changes.
3. **Given** the completed batch, **When** the PR is reviewed, **Then** Swift
   tracked source/test LOC is lower and no dependency, runtime-flow, API, data,
   or deploy change is present.

### Edge Cases

- If a file needs `Foundation` for compiler-visible symbols such as
  `CharacterSet`, `ProcessInfo`, `OperatingSystemVersion`, `Date`, `URL`,
  `Data`, dispatch primitives, locks, or property-wrapper/protocol symbols, keep
  the import intentionally and record why.
- If deleting an import requires adding a different import, defer it to a
  separate import-normalization slice unless the replacement is clearly smaller
  and directly proven.
- If a candidate only passes due to stale build artifacts, rerun SwiftPM build
  and focused validation before marking the task complete.

## Requirements

- **FR-001**: The batch MUST remove only `Foundation` import lines with compile
  evidence that they are unnecessary.
- **FR-002**: The batch MUST NOT add imports, dependencies, wrappers, helpers,
  abstractions, tests, or runtime code unless validation proves they are
  required.
- **FR-003**: The batch MUST keep any import that has a compiler-visible role,
  even if static text scanning makes it look removable.
- **FR-004**: The batch MUST report Swift tracked LOC delta separately from Spec
  Kit/docs changes.
- **FR-005**: The batch MUST run focused Swift validation for touched macOS
  surfaces and the repository closeout gate before PR/merge.
- **FR-006**: The batch MUST NOT perform production deploy or release work.

## Success Criteria

- **SC-001**: Swift tracked source/test LOC delta is negative for the
  implementation files.
- **SC-002**: `swift build --package-path apps/macos` succeeds after import
  deletion.
- **SC-003**: Focused Swift tests covering touched surfaces pass.
- **SC-004**: `infra/scripts/ci-local.sh` passes before closeout.

## Assumptions

- Import-only deletion does not require data-model or API-contract artifacts.
- Broader SwiftUI view slimming, file splits, dependency changes, and runtime
  refactors require separate evidence and separate Spec Kit slices.
