# Research: MVP Owner Journey Proof

## Decision: Treat 051 as a proof-and-fix slice

**Rationale**: Features 045 through 050 shipped the core recording,
processing, playback, outcomes, cabinet truth, and readiness proof surfaces.
The remaining work is not a broad rewrite. 051 should prove the current full
owner journey and apply only narrow fixes discovered by that proof.

**Alternatives considered**:
- Start a new UX redesign before proof. Rejected because it can break accepted
  behavior without first identifying remaining P1 failures.
- Declare MVP from 050. Rejected because 050 explicitly left fresh owner
  journey, stored production outcomes, and representative timing unproven.

## Decision: Use metadata-only production probes

**Rationale**: Production proof must inspect real state, but committed evidence
cannot contain meeting content or secrets. Probes should return counts,
statuses, durations, redacted identifiers, release SHA, and claim impact only.

**Alternatives considered**:
- Commit screenshots or transcript snippets from production review. Rejected
  unless fully sanitized and free of private content.
- Avoid production inspection. Rejected because the user asked for confidence in
  a real MVP, not only local tests.

## Decision: Stored outcomes are a P1 production proof gate

**Rationale**: 049 implemented stored outcomes, but 050 found the current
production candidate had missing outcomes. The MVP review must prove outcome
category states on a current production candidate or keep the gate open.

**Alternatives considered**:
- Accept fixture-backed outcome tests only. Rejected because fixture evidence
  does not prove the deployed production path.
- Require every category to have generated text. Rejected because truthful
  `not_found`, `not_inferable`, `blocked`, or `failed` states are safer than
  fabricated content.

## Decision: Measure timing without extrapolating short recordings

**Rationale**: The user-defined speed target is no more than three minutes for
one hour of audio. A short recording can prove the pipeline works, but it
cannot prove the one-hour target. The report must separate raw processing,
queue/wait, and finalize-to-review timing.

**Alternatives considered**:
- Scale a short run linearly. Rejected because MediaScribe and queue behavior
  may not scale linearly.
- Use only local benchmark tests. Rejected because the goal is production owner
  wait and production dependency behavior.

## Decision: Use Krisp only as interaction-pattern reference

**Rationale**: Krisp is useful as a reference for transcript-first review,
persistent bottom playback, timestamp seek, and speaker timeline lanes. 2brain
Rec must remain original and clean-room: no Krisp assets, screenshots, private
content, copy, icons, colors, or brand expression in committed artifacts.

**Alternatives considered**:
- Copy Krisp layout directly. Rejected by brand-distance and product gates.
- Ignore the reference. Rejected because the user explicitly wants the UI
  checked against that class of review/playback experience.

## Decision: Keep signed/notarized installer as P2 unless pilot distribution blocks

**Rationale**: Current repo scripts support local/ad-hoc installer validation.
Public signed/notarized distribution needs Apple credentials, packaging, and
release asset workflow. It is important, but not required to prove the internal
owner MVP journey unless pilot distribution depends on it.

**Alternatives considered**:
- Block 051 on notarized installer. Rejected because it would mix distribution
  hardening with owner journey proof.
- Hide installer limitation. Rejected because status must remain truthful.

## Decision: Final claim is evidence-gated

**Rationale**: `internal_pilot_candidate` is allowed only if every P1 051 gate
passes. If any P1 gate fails, is blocked, or is unproven, final claim remains
`pilot_blocked`. `production_ready` and broad `user_rollout_ready` remain out
of scope until a separate rollout gate proves them.

**Alternatives considered**:
- Treat `infra_smoke_ready` as pilot readiness. Rejected because infrastructure
  health does not prove the owner product loop.
- Use aspirational release notes. Rejected because the project requires
  evidence-backed Russian release notes.
