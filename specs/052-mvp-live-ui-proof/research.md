# Research: MVP Live Owner Journey And UI Proof

## Decision: Treat 052 as proof-and-fix, not a redesign

**Rationale**: 045-051 already shipped the recording, processing, playback,
outcomes, cabinet truth, and launch-readiness machinery. The remaining MVP
question is whether the whole owner path works now on production and whether
the UI is coherent enough to use. The smallest correct slice is to prove the
current path and patch only defects found by that proof.

**Alternatives considered**:
- Start a new visual redesign. Rejected because it delays the live evidence
  needed to know what is actually broken.
- Declare MVP from existing component tests. Rejected because 051 left the
  fresh owner journey, production outcomes, and long timing gates open.

## Decision: Require direct current production evidence for P1 gates

**Rationale**: Local fixtures and older production candidates are useful
regression evidence, but they do not prove the currently deployed product can
carry a fresh owner recording to review. P1 gates need current production
metadata or must remain open.

**Alternatives considered**:
- Extrapolate from 051's short production candidate. Rejected because it
  predates the accepted 049/050 release train and has no stored outcomes.
- Use screenshots or transcript snippets. Rejected because committed evidence
  must stay metadata-only.

## Decision: Keep outcomes truth state-based, not text-based

**Rationale**: The MVP needs stored outcome availability and category truth,
not a guarantee that every category has generated text. `not_found`,
`not_inferable`, `blocked`, and `failed` are valid truthful states when source
segments do not support a claim.

**Alternatives considered**:
- Require generated text in every category. Rejected because it encourages
  fabrication.
- Treat missing outcome rows as acceptable. Rejected because 049 made stored
  outcomes part of the MVP review promise.

## Decision: Timing proof must be representative or remain open

**Rationale**: The user target is no more than 180 seconds of processing per
one hour of audio. A short smoke run proves pipeline health only. A pass
requires representative long-audio timing, or the gate stays open.

**Alternatives considered**:
- Linear extrapolation from short audio. Rejected because queueing, provider
  processing, and import behavior may not scale linearly.
- Local-only timing benchmark. Rejected as insufficient for production MVP
  readiness, though it may be useful as supporting evidence.

## Decision: Follow the approved observable Krisp reference

**Rationale**: Constitution VII and PRD §§29–30 supersede the original June
brand-distance rule. Observable UX/UI/IA and functional wording may match
literally. Code stays independent; extracted assets, source, binaries, private
APIs, secrets and private content are prohibited. Third-party assets and marks
need documented rights. Accessibility, localization and GRAF trust gates may
require documented deviations.

The original speaker-assignment and multi-speaker observation scope is retained:
inspect assignment affordances, association of labels with transcript/lanes,
and unavailable states under the interface contract. This does not add a
post-MVP editor or authorize changes to real meetings.

**Alternatives considered**:
- Preserve the old blanket color/layout/wording prohibition. Rejected because
  it contradicts the current product decision.
- Copy competitor code/assets/private content. Rejected; reference permission
  does not grant those rights.

## Decision: Auth/session blockers do not become green UI

**Rationale**: 047 fixed false-green cabinet state. 052 must preserve that
truth: production health, a configured URL, or a login page cannot be treated
as ready owner review.

**Alternatives considered**:
- Treat server health as cabinet readiness. Rejected because the user already
  saw why that is misleading.
- Bypass auth in evidence. Rejected unless the proof clearly labels it as
  fixture/local evidence rather than production owner proof.

## Decision: Raise readiness only when every P1 gate passes

**Rationale**: `internal_pilot_candidate` is allowed only if the fresh owner
journey, production stored outcomes, representative timing, and UI proof all
pass. Any failed, blocked, or unproven P1 gate keeps the claim at
`pilot_blocked`.

**Alternatives considered**:
- Raise readiness with caveats. Rejected because the project uses explicit
  launch gates to avoid ambiguous claims.

## Decision: T020 reports scoped API metadata

**Rationale**: the existing probe returns pass after any successful JSON and
reads top-level status although the route returns `MeetingReviewResponse` with
`meeting.status`. Current API models and stored outcome mapper define the
observed fields; the owner contract now fixes their strict types, counts,
positive/negative classification, health aggregate and exit behavior. An API
observation cannot attest to fresh capture, UI seek/visibility or timing.

The response meeting UUID must match the requested UUID before metadata can
pass. This is the API identity already exposed by MeetingListItem, not proof of
freshness or persisted revision lineage. Missing/malformed identity fails schema
validation; a different valid UUID fails with a fixed candidate_mismatch reason.

**Alternatives considered**:
- Keep HTTP200 or nested-ready alone as pass. Rejected by the reproduced
  empty/processing/ready-without-artifacts false positives.
- Require positive text in every outcome. Rejected: stored not_found and
  not_inferable are honest empty states; protocol risks have an explicit
  non-blocking projection. A generic non_blocking flag is insufficient.
- Change server readiness or generate missing artifacts. Rejected; this repair
  changes only how the evidence tool reports its existing observation.

PR #8126 review identified that protocol was initially read at the category
level. The actual `NotesActionTruthState.protocol` and
`stored_outcome_truth_state` put it at `notes_action_truth.protocol`, alongside
categories. The contract now uses this source explicitly; a category-only
protocol cannot enable the exception. Earlier passing synthetic fixtures used
the wrong nesting and do not prove this real response case.

## Decision: Separate requirement quality from live acceptance

**Rationale**: historical requirements checklist R15 literally asks whether
measurable product outcomes already hold. That is an acceptance gate, while
pre-implementation checklists test the completeness of the requirements. The
owner proposes explicit wording about defined acceptance evidence, keeping
actual outcomes in SC-001/003/004, T019/T020 and the P1 gate table unchanged.
The original R15 wording and STOP remain recorded in the review history; only
the independent reviewer may assess the revised item and change its mark.

**Alternatives considered**:
- Mark historical R15 complete from source/tests. Rejected: no fresh live
  acceptance exists.
- Remove fresh journey or UI acceptance. Rejected: repairing a probe cannot
  finish those original criteria.
