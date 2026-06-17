# Research: MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

## Decision: Treat 035 As Validation-Only

The slice will not add missing product behavior. It may update readiness
classification, reports, evidence files, tests, and status docs only when those
changes make the current state more truthful.

**Rationale**: The user asked to move toward MVP without overclaiming. If a
capability is missing, the correct output is a blocker or follow-up slice, not a
hidden implementation inside a validation pass.

**Alternatives considered**:

- Implement notes/actions in 035. Rejected because that is a product capability
  and needs its own specification.
- Ship production changes in 035. Rejected because production deploy changes
  require separate deployment gates.

## Decision: Use `/Applications/2brain Rec.app` As Desktop Proof Source

Manual desktop evidence must launch the permissioned installed app path and
record the process path, screenshots, and latest artifact validation.

**Rationale**: macOS privacy permissions are bound to bundle identity/path in
practice. The user explicitly asked to launch from `/Applications` after granting
permissions there.

**Alternatives considered**:

- Use the repo `.build` app. Rejected for acceptance because it can have
  different permission state.
- Use `~/Applications`. Rejected for acceptance after the user's latest
  instruction selected `/Applications`.

## Decision: Allow Safe Fixture Web Evidence When Live Web Content Is Private

Web owner review can be proven with live metadata-safe routes or safe fixture
data, but the evidence must label which mode was used.

**Rationale**: The repo must not commit private meeting content. A truthful
fixture-backed state is stronger than unsafe live screenshots.

**Alternatives considered**:

- Require private live meeting screenshots. Rejected by the data boundary.
- Skip web evidence. Rejected because the MVP loop includes owner review.

## Decision: Strong Claims Require Zero P0/P1 Launch Gaps

`mvp_loop_ready` and pilot/user rollout claims remain forbidden while any P0/P1
gap lacks strong evidence.

**Rationale**: Existing readiness models enforce this invariant. 035 should
make the claim decision more current, not relax it.

**Alternatives considered**:

- Allow pilot candidate with known P1 blockers. Rejected by product truth rules.
- Collapse all blockers into one narrative note. Rejected because owner area and
  next action traceability are required.

## Decision: Clean-Room Reference Comparison Is Evidence, Not Design Copying

035 will record allowed reference lessons, intentional differences, and
forbidden similarity checks. It will not commit private Krisp screenshots or
copy brand/copy/layout.

**Rationale**: The user wants quality matched to the reference app/web, but the
constitution requires original 2brain design and brand-distance review.

**Alternatives considered**:

- Use reference screenshots directly as committed assets. Rejected unless they
  are proven safe and necessary.
- Ignore reference app/web. Rejected because visual/product quality is part of
  launch readiness.
