# Feature Specification: Dead Code Batch 3

**Feature Branch**: `codex/076-dead-code-batch-3`

**Created**: 2026-07-01

**Status**: Draft

**Input**: Continue the Ponytail cleanup program after 075 by removing only
code with direct evidence that it is unnecessary. Do not broaden into an
architecture split or rewrite.

## User Scenarios & Testing

### User Story 1 - Remove Proven Unused Imports (Priority: P1)

As a product maintainer, I want the next cleanup batch to remove only imports
that the Swift compiler proves are unnecessary, so the macOS codebase gets
smaller without changing product behavior.

**Why this priority**: Import-only deletion is the smallest safe next step after
the zero-reference helper scan found no further private helper candidates.

**Independent Test**: The batch is independently testable by compiling the
macOS package and running focused tests for the touched surfaces.

**Acceptance Scenarios**:

1. **Given** a fresh checkout from `origin/master`, **When** the candidate import
   lines are removed, **Then** `swift build --package-path apps/macos` succeeds.
2. **Given** the import-only deletion diff, **When** focused macOS validation
   runs for capture, routing, and Bluetooth policy surfaces, **Then** the tests
   pass with no product-behavior changes.
3. **Given** the completed batch, **When** the PR is reviewed, **Then** the
   Swift source delta is negative and no dependency, runtime-flow, or deploy
   change is present.

### Edge Cases

- If an import provides compiler-visible protocol or property-wrapper symbols,
  keep it intentionally and record why.
- If deleting an import requires adding a different import, defer it unless the
  replacement is clearly smaller and more direct.
- If build success depends on unrelated cached artifacts, rerun clean enough
  validation through SwiftPM and the repository gate.

## Requirements

- **FR-001**: The batch MUST remove only import lines with compile evidence that
  they are unnecessary.
- **FR-002**: The batch MUST NOT add imports, dependencies, wrappers, helpers,
  abstractions, or tests unless a compile/test failure proves they are required.
- **FR-003**: The batch MUST keep any import that has a compiler-visible role,
  even if it looks surprising in a source scan.
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
- Broader SwiftUI view slimming, file splits, and dependency policy changes
  require separate evidence and separate Spec Kit slices.
