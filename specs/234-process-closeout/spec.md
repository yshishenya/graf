# Feature Specification: Process Closeout And Issue Truth

**Feature Branch**: `codex/234-process-closeout`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User request to finish the development-process migration, prevent
parallel-worktree and CI races, and stop features from leaving GitHub issues
open or closed without evidence.

## User Scenarios & Testing

### User Story 1 - Reserve and start work safely (Priority: P1)

An agent starts a new feature from a clean worktree and receives a fresh,
traceable Feature ID and umbrella issue without scanning an unbounded history or
mistaking its own requested branch for a collision.

**Why this priority**: A wrong identity contaminates every later PR, issue and
release record.

**Independent Test**: Run the allocator against the public repository and
verify a bounded exact GitHub lookup, a canonical open umbrella issue and a
complete per-worktree pointer.

**Acceptance Scenarios**:

1. **Given** a clean worktree and an unused next marker, **When** allocation is
   requested, **Then** the script creates one labelled umbrella issue and
   writes the exact branch, source SHA and feature directory.
2. **Given** the requested branch already exists locally, **When** allocation is
   requested for that branch, **Then** it is treated as the reservation being
   made rather than as a collision.

### User Story 2 - Ship a feature with truthful issue state (Priority: P1)

The feature owner can map every executable task to one GitHub issue and close an
issue only after acceptance criteria and validation evidence are recorded.

**Why this priority**: Silent task/issue drift was the main source of apparently
finished features with unfinished work.

**Independent Test**: Validate a feature with complete task checkboxes and
closure comments, then validate a fixture with an open task or missing closure
evidence and observe a fail-closed result.

**Acceptance Scenarios**:

1. **Given** a completed task and passing exact-SHA checks, **When** the issue is
   closed, **Then** a Russian closure comment names the task, PR and evidence.
2. **Given** an unchecked task or missing evidence, **When** closeout is
   attempted, **Then** the process keeps the issue open and records the gap.

### User Story 3 - Keep agent context and PR instructions bounded (Priority: P2)

An agent working in one worktree loads stable rules plus only the active feature
artifacts; PR templates clearly identify GitHub Actions as authoritative and
local CI as diagnostic fallback.

**Why this priority**: Bounded context prevents accidental edits to another
feature and removes the local-CI race from the normal path.

**Independent Test**: Inspect the root router and both PR templates, then run
the governance validators on a PR body containing the required Feature ID,
issue links, lane, SHA and Legacy Impact fields.

**Acceptance Scenarios**:

1. **Given** several worktrees, **When** an agent starts, **Then** the active
   pointer selects one feature without mtime or shared mutable context.
2. **Given** a PR, **When** its checks are described, **Then** the required
   gate is `governance-fast` on GitHub and a local receipt cannot replace it.

## Edge Cases

- GitHub search or issue creation times out: allocation fails closed and does
  not write a claim.
- A requested feature marker exists in a PR body but not a title: exact body
  and label searches still detect it.
- A PR changes SHA after a passing check: the evidence is stale and must not
  close an issue.
- GitHub auto-closes an issue before the detailed closure comment is added:
  add the comment immediately and reconcile tasks before declaring closeout.
- A worktree is dirty or detached: preserve it and use a fresh disposable
  worktree for the feature.

## Requirements

### Functional Requirements

- **FR-001**: The feature allocator MUST use bounded exact GitHub searches for
  candidate markers during online claim/allocation and MUST fail closed on
  lookup errors.
- **FR-002**: Allocation MUST exclude the requested local/origin branch from
  collision detection and MUST create exactly one canonical labelled umbrella
  issue before writing the shared claim record.
- **FR-003**: Every executable task MUST map to an issue, and closeout MUST
  require every mapped task to be checked and validated on the exact SHA.
- **FR-004**: A fully closed issue MUST have a Russian closure comment naming
  what changed, why it matters, validation evidence, out-of-scope items, the
  Spec Kit task and PR.
- **FR-005**: A closed issue whose mapped task is still open MUST be reported as
  inconsistent and MUST NOT be silently treated as complete.
- **FR-006**: PR templates MUST state that GitHub `governance-fast` is the
  authoritative merge gate and local `ci-local.sh` is manual diagnostic or
  offline fallback only.
- **FR-007**: Root agent guidance MUST keep stable rules separate from active
  per-worktree feature context and MUST prohibit root `CHANGELOG.md` edits by
  feature agents.

### Key Entities

- **Feature claim**: Feature ID, umbrella issue, branch, slug and source SHA.
- **Task record**: A checked or unchecked Spec Kit task linked to one GitHub
  issue and validation evidence.
- **Closure evidence**: A Russian issue comment plus exact-SHA check references
  and scope statement.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Online allocation completes in under 15 seconds on the current
  public repository when the candidate is free, without a full issue-history
  pagination request.
- **SC-002**: Governance validation rejects 100% of fixtures with an unchecked
  mapped task or missing closure evidence.
- **SC-003**: Both PR templates contain the same authoritative GitHub/local-CI
  contract and pass the repository governance checks.
- **SC-004**: Feature 233's previously drifting task/issue state is reconciled
  with checked tasks and a detailed closure comment linked to the exact PR
  checks.

## Assumptions

- GitHub Actions remains enabled and `governance-fast` remains the required
  branch-protection check.
- The sole repository owner may merge with zero required approvals when all
  recorded agent/owner review and required checks pass.
- Existing `infra/scripts/ci-local.sh` remains available and is not removed.
- Legacy removal is a subsequent feature; this closeout only prevents new
  legacy and records retirement work honestly.

## Legacy Impact

Classification: `untouched`
owner: feature owner
expiry: 2026-12-31
removal trigger: follow-up legacy-retirement feature after process closeout
risk: no new runtime fallback or alias is introduced
validation: governance legacy-impact validator and PR Legacy Impact gate
reason: existing local CI fallback and historical compatibility remain required
