# Research: MVP Launch Proof

## Decision: Use a proof-first feature slice

**Rationale**: The major MVP capabilities have been implemented across earlier
features, but current truth is scattered across release notes, status docs,
fixture tests, production smokes, and manual app evidence. The next value is to
prove the whole owner loop and fix only concrete gaps found during proof.

**Alternatives considered**:
- Start a broad rewrite of the web/app UI. Rejected because it risks breaking
  accepted playback/outcomes behavior before we know which gaps remain.
- Declare MVP from existing release closeouts. Rejected because stale status and
  production user-journey gaps remain.

## Decision: Keep live evidence metadata-only

**Rationale**: This feature must inspect real production and installed-app
behavior, but committed artifacts cannot contain raw audio, transcript text,
private meeting titles, account identifiers, cookies, tokens, signed URLs,
object keys, or local private paths. Evidence should store route families,
counts, state names, durations, release tags, commit SHAs, pass/fail status, and
redacted screenshots only when safe.

**Alternatives considered**:
- Commit live screenshots of review pages. Rejected unless the screenshot is
  explicitly sanitized and contains no private content.
- Store transcript snippets for comparison. Rejected by product gates.

## Decision: Use Krisp only as clean-room interaction reference

**Rationale**: Krisp is useful for interaction patterns: transcript-first
review, persistent bottom playback, seekable timestamps, and speaker activity
lanes. 2brain Rec must use original design, copy, colors, assets, and icons.

**Alternatives considered**:
- Copy Krisp visual details. Rejected by brand-distance and clean-room gates.
- Ignore the reference entirely. Rejected because the user explicitly wants the
  playback/review ergonomics checked against that class of product.

## Decision: Readiness claim is evidence-gated

**Rationale**: The final output should state exactly one claim. If all P1 gates
pass, the strongest allowed claim is `internal_pilot_candidate`. If any P1 gate
fails or remains unproven, the claim stays `pilot_blocked` with a concrete next
fix path. `production_ready` and broad `user_rollout_ready` require stronger
rollout evidence than this internal MVP proof.

**Alternatives considered**:
- Treat deployment smoke as enough for pilot readiness. Rejected because infra
  smoke does not prove the owner journey.
- Treat old fixture proof as enough for UI readiness. Rejected because the user
  asked to recheck the real web cabinet and app.

## Decision: Processing-time target is measured, not assumed

**Rationale**: The product target is no more than three minutes of processing
for one hour of audio. 050 records direct timing evidence for a long or
representative recording when available. If only a short recording is available,
the target must be marked unproven rather than inferred.

**Alternatives considered**:
- Use synthetic unit benchmark as proof. Rejected because it does not include
  production MediaScribe behavior.
- Ignore the timing target until later. Rejected because it is part of the
  user's MVP definition.

## Decision: Correct public URL governance drift before planning

**Rationale**: The constitution and product gates had stale `rec.2brain.dev`
public URL text while PRD, infra scripts, tests, and production releases use
`https://rec.2brain.pro`. 050 needs a clean constitution check, so the drift was
corrected as a patch-level governance update.

**Alternatives considered**:
- Leave both URLs and explain in the plan. Rejected because constitution rules
  are non-negotiable and should not contradict deploy evidence.
