# Feature Specification: Dead Code Batch 2

**Feature Branch**: `codex/075-dead-code-batch-2`

**Created**: 2026-07-01

**Status**: Draft

**Input**: Continue Ponytail cleanup after 074. Remove only Swift helpers with
direct zero-reference evidence. Do not split files or introduce abstractions.

## Clarifications

### Session 2026-07-01

- Q: Is this another architecture split? -> A: No. This is deletion-only cleanup.
- Q: Can candidates be removed without caller evidence? -> A: No.
- Q: Deploy? -> A: No production deploy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Dead Swift Helpers (Priority: P1)

As a maintainer, I want Swift helpers with zero references removed in a small
reviewable batch, so that macOS code gets smaller without changing desktop
behavior.

**Why this priority**: 074 established that cleanup must reduce runtime code.
This continues that rule in the macOS surface.

**Independent Test**: Removed helper names no longer appear in source/tests and
the focused Swift test target for the touched paths passes.

**Acceptance Scenarios**:

1. **Given** a private Swift helper has no references outside its definition,
   **When** the helper is removed, **Then** the touched target still builds/tests
   and the helper name has no remaining matches.
2. **Given** a candidate is only suspected dead, **When** direct reference
   evidence is incomplete, **Then** it is not removed in this batch.

### Edge Cases

- SwiftUI private helpers can be referenced only from view builders in the same
  file, so same-file search must be included.
- Test-only helpers are safe to remove only when no test call remains.
- Capture and desktop visible-state behavior must not change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Remove only the two candidates recorded in `audit-candidates.md`
  when direct zero-reference evidence remains true.
- **FR-002**: Do not move, split, or rename surrounding Swift code.
- **FR-003**: Do not add dependencies, abstractions, or new runtime files.
- **FR-004**: Preserve desktop capture visibility and cabinet behavior.
- **FR-005**: Report Swift runtime/test LOC delta separately from Spec Kit/docs
  delta.
- **FR-006**: Do not run production deploy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Swift source/test LOC delta is negative for the implementation
  batch.
- **SC-002**: Removed helper names have zero matches after deletion.
- **SC-003**: Focused Swift validation passes for touched paths.
- **SC-004**: No dependency files change.

## Assumptions

- This slice starts from `origin/master` after merged 074.
- Existing Swift package/test configuration remains the validation source of
  truth.
