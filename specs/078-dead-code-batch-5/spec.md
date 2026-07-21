# Feature Specification: Dead Code Batch 5

**Feature Branch**: `codex/078-dead-code-batch-5`

**Created**: 2026-07-01

**Status**: Implemented import/dead-code cleanup; no deploy or product behavior change

**Input**: User request to continue Ponytail cleanup carefully: improve the
product by removing dead code and unnecessary lines, not by broad rewrites or
speculative splitting.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep The Desktop Runtime Lean (Priority: P1)

As the product owner, I want a small, evidence-backed cleanup batch that removes
unneeded source lines while preserving the current desktop recording, buffering,
and route-safety behavior.

**Why this priority**: The product should become simpler without increasing
risk in capture-adjacent shared code.

**Independent Test**: The cleanup is independently testable by comparing the
source line count before and after the batch and running the focused validation
for the touched shared desktop surfaces plus the repository closeout gate.

**Acceptance Scenarios**:

1. **Given** a candidate line that appears unused, **When** the candidate lacks
   compile/runtime evidence, **Then** the batch must leave it in place and
   classify it as intentionally kept or needing a separate spec.
2. **Given** a compile-proven unused import in shared desktop source, **When**
   it is removed, **Then** all focused validation and the repository closeout
   gate must pass with no product behavior change.

### Edge Cases

- If a candidate import is the only visible provider of a language or platform
  symbol, it must not be removed in this batch without a successful compile
  probe.
- If a candidate merely narrows an import but does not reduce source lines, it
  should be deferred unless it materially reduces risk.
- If a cleanup candidate touches capture, buffering, diagnostics, or route
  safety, focused validation must cover the nearby behavior.
- If `origin/master` moves during validation, the branch must be refreshed and
  affected validation rerun before closeout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The batch MUST only remove lines classified as compile-proven
  unused or explicitly harmless after focused validation.
- **FR-002**: The batch MUST NOT change desktop recording, buffering,
  route-truth, diagnostic redaction, privacy, deletion, upload, auth, or deploy
  behavior.
- **FR-003**: The batch MUST record each reviewed candidate as `delete now`,
  `keep intentionally`, or `risky / needs spec`.
- **FR-004**: The batch MUST report tracked source line-count delta before and
  after implementation.
- **FR-005**: The batch MUST preserve Ponytail constraints: no new dependency,
  no new abstraction, no new tool, and the smallest working diff.
- **FR-006**: The batch MUST run focused validation for touched shared desktop
  surfaces and the repository closeout gate before PR/merge.
- **FR-007**: The batch MUST NOT trigger a production deploy or release train.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one source line is removed from tracked macOS Swift
  sources, and no source line is added to replace it.
- **SC-002**: 100% of removed lines are listed in the audit evidence with a
  `delete now` classification.
- **SC-003**: 100% of reviewed but retained candidates are listed with the
  reason they were not changed in this batch.
- **SC-004**: Focused Swift validation and `infra/scripts/ci-local.sh` pass
  before the PR is considered ready.
- **SC-005**: The PR body records the selected risk/validation lane, no-deploy
  boundary, line-count delta, and issue links.

## Assumptions

- The active cleanup lane is a full Spec Kit slice because touched files are
  shared and capture-adjacent, even though the intended diff is import-only.
- No schema, data model, external contract, release, or deploy artifact changes
  are expected.
- Candidates that require behavior interpretation rather than compile evidence
  belong to a later, separately scoped cleanup batch.
