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

## Decision: Use KRISP as clean-room interaction reference only

**Rationale**: KRISP helps define owner expectations for transcript-first
review, persistent bottom playback, speaker lanes, timestamp seek, and assign
speaker affordances. 2brain Rec must stay original and must not copy KRISP
assets, colors, icons, private content, wording, or brand expression.

**Alternatives considered**:
- Copy KRISP layout directly. Rejected by brand-distance rules.
- Ignore the reference. Rejected because the user explicitly asked to inspect
  and compare web/app reference behavior.

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
