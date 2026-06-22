# Feature Specification: WebRTC AEC3 Speakerphone Spike

**Feature Branch**: `039-webrtc-aec3-speakerphone-spike`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Continue the clean-recording plan after 038. Evaluate WebRTC AEC3 as the next candidate for preventing speaker audio from leaking into the microphone track."

## Program Context

Features `037`-`041` are the clean-recording chain from
`docs/audio-capture-backlog.md`. Feature `037` gave 2brain Rec an app-owned
microphone sample graph for recording. Feature `038` proved that Apple voice
processing remains metadata/guidance evidence only and recorded the primary
outcome `defer_to_webrtc_aec3`.

This feature activates only feature `039`: a bounded WebRTC AEC3 speakerphone
spike. Its job is to determine whether 2brain Rec can truthfully produce a
cleaner built-in speakerphone microphone candidate by comparing microphone input
against the known incoming meeting audio reference.

This feature must not treat the existence of an echo-cancellation algorithm, a
synthetic pass, or a single good recording as proof that 2brain Rec can claim
clean dual-track speakerphone recording. The result must be evidence-driven,
fail-closed, and safe for package truth, diagnostics, licensing, and
user-facing copy.

Follow-up slices remain separate:

- `040-speakerphone-recording-fallback-decision`
- `041-recording-permission-readiness-onboarding`

## Clarifications

### Session 2026-06-22

- Q: If 039 proves WebRTC AEC3 works, may the accepted candidate become the main
  recording/transcription track immediately? -> A: Yes, but only after a much
  larger validation gate passes across expanded datasets, sliced test windows,
  and the full test file; a small spike pass is not enough.
- Q: What minimum expanded validation corpus is enough before immediate
  promotion? -> A: A lab-grade corpus: at least ten files per required scenario
  family, at least two room conditions, two Mac/device profiles, three volume
  levels, five slices from every file, and full file validation of every file.
- Q: Is the lab-grade file corpus enough for immediate promotion, or is real app
  recording evidence required too? -> A: The lab-grade corpus must pass, and
  controlled real-hardware recording through the app on a physical Mac must pass
  for the enumerated real-hardware scenarios with metadata-only evidence.
- Q: If AEC3 passes, what route scope may be promoted or claimed? -> A:
  Promotion and user-facing clean speakerphone claims are limited to built-in
  Mac microphone plus built-in Mac speakers; other route classes remain
  supporting evidence only unless separately validated later.
- Q: If AEC3 is promoted and runtime evidence becomes uncertain, what should the
  product do? -> A: Promotion must be reversible; route changes, missing
  reference, quality drops, or incomplete evidence automatically return to
  original microphone truth and remove the clean-recording claim.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classify WebRTC AEC3 Feasibility For Built-In Speakerphone (Priority: P1)

As a product owner, I need a clear go/no-go classification for WebRTC AEC3 on
built-in Mac microphone plus built-in Mac speakers, so the product can decide
whether it is safe to move toward clean speakerphone recording.

**Why this priority**: 038 deferred Apple processing to WebRTC AEC3. Built-in
speakerphone remains the highest-risk user promise because false acceptance
would create polluted microphone recordings while telling the user they are
clean.

**Independent Test**: Run the 039 validation matrix on the built-in microphone
and built-in speakers route, compare the unprocessed microphone baseline with a
WebRTC AEC3 candidate, and record exactly one outcome with metadata-only
evidence.

**Acceptance Scenarios**:

1. **Given** the app has separate incoming-audio and microphone evidence, **When**
   WebRTC AEC3 is evaluated on built-in mic plus built-in speakers across the
   lab-grade validation corpus, **Then** the spike records whether the route is
   accepted for immediate promotion, blocked, derived-candidate only,
   guidance-only, or deferred without making a clean recording claim unless all
   gates pass.
2. **Given** remote meeting audio is playing and the local user is silent,
   **When** the candidate microphone evidence is compared with the unprocessed
   baseline, **Then** the result records residual leakage, confidence, and whether
   the candidate meets the declared residual-leakage threshold for promotion.
3. **Given** local speech and remote audio overlap, **When** the candidate is
   evaluated during double-talk, **Then** the result records whether local speech
   remains usable rather than being suppressed, distorted, or gated out.

---

### User Story 2 - Preserve Recording Truth While Comparing Candidate Audio (Priority: P1)

As an engineering owner, I need every AEC3 candidate to be traceable without
silently replacing original recording evidence, so review, transcription, and
fallback decisions stay honest.

**Why this priority**: A cleaner candidate is useful only if it does not destroy
the ability to inspect the original microphone and incoming audio tracks. The
product must avoid turning an experimental processing result into hidden package
truth.

**Independent Test**: Produce a controlled recording package with an AEC3
candidate and verify that original tracks, candidate lineage, timing, and final
package status are all represented separately and consistently.

**Acceptance Scenarios**:

1. **Given** an AEC3 candidate exists, **When** a recording package is finalized
   before all immediate-promotion gates pass, **Then** the package distinguishes
   original microphone evidence, incoming reference evidence, derived/candidate
   evidence, and final package truth.
2. **Given** the candidate passes all immediate-promotion gates, **When** package
   readiness is computed, **Then** the accepted candidate may become the main
   microphone source for recording/transcription while the original tracks remain
   traceable for audit and fallback.
3. **Given** candidate timing, reference availability, or speech preservation is
   uncertain, **When** evidence is recorded, **Then** the outcome remains blocked
   or unproven and original package truth remains authoritative.
4. **Given** the lab-grade file corpus passes, **When** the candidate is validated
   through a controlled real-hardware app recording on a physical Mac, **Then**
   package truth, candidate lineage, Stop behavior, and metadata-only evidence
   must still pass before promotion is allowed.
5. **Given** an accepted candidate is active for the 039 route, **When** route,
   reference, quality, timing, or lineage evidence becomes uncertain, **Then** the
   package returns to original microphone truth and removes the clean-recording
   claim until the promotion gates pass again.

---

### User Story 3 - Fail Safely Under Real Speakerphone Conditions (Priority: P1)

As a privacy and capture-safety owner, I need WebRTC AEC3 failures to be visible,
bounded, and metadata-only, so the spike cannot hide capture, leak content, hang
recording, or promote uncertain audio.

**Why this priority**: Echo cancellation can fail because of delay, jitter,
call-order mistakes, clipping, route changes, missing reference audio,
double-talk, CPU load, or device changes. Every failure must be safer than a
false clean-recording claim.

**Independent Test**: Exercise missing/late reference audio, silence, loud
speakers, clipping, route changes, double-talk, Stop, quit, and diagnostics
while candidate evidence is active. Confirm bounded outcomes, one-action Stop,
and metadata-only diagnostics.

**Acceptance Scenarios**:

1. **Given** the incoming-audio reference is missing, late, protected, silent, or
   inconsistent with the sound reaching speakers, **When** candidate evaluation
   completes, **Then** the route is blocked or unproven rather than accepted.
2. **Given** the user changes microphone, output, volume, route, or meeting
   target during validation, **When** recording continues or stops, **Then** the
   product preserves visible active capture, Stop, and package truth.
3. **Given** diagnostics are exported after any candidate result, **When** the
   evidence is inspected, **Then** it contains only bounded counters, route
   classes, status fields, reason codes, thresholds, timing summaries, and
   licensing/readiness status.
4. **Given** AEC3 candidate evaluation, rollback, or fallback-relevant problems
   occur while the app is visible, **When** the user checks recording status,
   **Then** the app shows a calm local status that identifies the current state,
   whether original microphone truth is being used, and whether action is needed
   without exposing meeting content.

---

### User Story 4 - Decide Whether To Promote AEC3 Or Move To Fallback (Priority: P2)

As a product and technical owner, I need the spike to produce one decision record
that says whether AEC3 can become a product path, remains only a derived
candidate, is blocked, or requires the fallback decision in 040.

**Why this priority**: 039 should reduce uncertainty. If it works, it creates the
first product-owned cleanup candidate. If it does not, 040 must choose a truthful
fallback without reopening the same questions.

**Independent Test**: Review the completed evidence and confirm it maps to one
primary outcome with supporting validation rows, limitations, and the next
recommended feature path.

**Acceptance Scenarios**:

1. **Given** all required validation rows are complete, **When** the spike is
   summarized, **Then** exactly one primary outcome is selected and linked to
   supporting evidence.
2. **Given** AEC3 is not accepted for built-in speakerphone, **When** the decision
   record is published, **Then** it directs the product to `040` fallback
   planning rather than relaxing clean-recording gates.
3. **Given** non-built-in route classes have supporting validation rows, **When**
   the decision record is published, **Then** those rows do not broaden the 039
   promotion scope beyond built-in Mac microphone plus built-in Mac speakers.

### Edge Cases

- Incoming meeting audio is silent, absent, protected, clipped, delayed, jittery,
  or not the same signal that reaches physical speakers.
- Render/reference evidence and capture evidence arrive in an unsafe order or
  with unstable delay.
- The user speaks while remote audio is playing, creating double-talk.
- Built-in speakers are loud enough to clip or overload the microphone.
- The user switches microphone, output, route, meeting target, volume, mute
  state, or display/audio route before or during recording.
- Bluetooth, AirPods, USB headset, wired-headphone, or browser-target evidence
  looks favorable but has not passed a separate full route-specific gate.
- Candidate processing improves leakage but damages local speech intelligibility.
- Candidate processing preserves speech but does not reduce leakage enough.
- Candidate timing drifts from original microphone and incoming tracks.
- Candidate evidence is available only for synthetic tests, not real package
  truth.
- Candidate evidence passes offline corpus validation but fails controlled
  real-hardware recording through the app.
- A previously accepted candidate encounters a route change, missing reference,
  degraded quality, timing uncertainty, or incomplete lineage during recording.
- App status is stale, overly technical, too noisy, or inconsistent with package
  truth after candidate evaluation, rollback, fallback planning, Stop, or route
  changes.
- CPU, memory, latency, Stop, quit, or no-hang behavior regresses.
- Licensing, redistribution, patent, packaging, signing, or notarization review
  is incomplete.
- Diagnostics, evidence files, decision records, or logs accidentally include raw
  audio, transcript text, credentials, signed URLs, private local paths, or
  meeting content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The spike MUST start from the merged `037` microphone sample graph
  and the merged `038` decision that Apple processing deferred to WebRTC AEC3.
- **FR-002**: The spike MUST classify WebRTC AEC3 with one primary outcome:
  `accepted_for_immediate_promotion`, `accepted_for_derived_candidate_only`,
  `accepted_for_guidance_only`, `blocked_route_topology`, `blocked_quality`,
  `blocked_stability`, or `defer_to_fallback_decision`. The immediate-promotion
  outcome applies only to built-in Mac microphone plus built-in Mac speakers.
- **FR-003**: The spike MUST compare an unprocessed microphone baseline with a
  candidate echo-reduced microphone result for the same route class and scenario.
- **FR-004**: The spike MUST use the known incoming meeting audio as the reference
  for candidate evaluation and MUST fail closed when that reference is missing,
  late, protected, silent, clipped, or not representative of speaker playback.
- **FR-005**: The spike MUST record reference/capture timing confidence and MUST
  fail closed when delay, jitter, or call-order evidence is unsafe.
- **FR-006**: The spike MUST verify far-end-only leakage reduction, near-end-only
  speech preservation, and double-talk behavior before any accepted
  immediate-promotion outcome is allowed.
- **FR-006a**: Immediate promotion MUST require a lab-grade validation corpus:
  at least ten test files for each required scenario family, at least five
  sliced windows from every file, and full-file validation for every file.
- **FR-006b**: The required scenario families for immediate promotion MUST
  include far-end-only leakage, near-end-only local speech, double-talk,
  loud-speaker/clipping stress, route-change/timing stress, and missing/late or
  unsafe-reference negative controls.
- **FR-006c**: The lab-grade corpus MUST represent varied room acoustics,
  physical Mac/device profiles, and speaker-volume levels: at least two
  acoustic conditions, at least two Mac/device profiles, and at least three
  speaker-volume levels. Missing room, device, or volume variation blocks
  immediate promotion but may still support a derived-candidate or guidance-only
  outcome.
- **FR-006d**: Immediate promotion MUST require controlled real-hardware
  recording validation through the app on a physical Mac for the critical
  scenario families; this validation may use consented test signals and MUST
  produce metadata-only evidence.
- **FR-006e**: Immediate promotion MUST be reversible: route changes, missing or
  unsafe reference audio, quality drops, timing uncertainty, lineage gaps, or
  incomplete metadata MUST automatically return package truth to the original
  microphone evidence and remove the clean-recording claim until gates pass
  again.
- **FR-006f**: Immediate promotion MUST use a versioned acceptance-threshold
  profile declared before validation begins, covering residual leakage, local
  speech preservation, double-talk confidence, timing drift, clipping/dropout,
  CPU/no-hang behavior, Stop/quit behavior, diagnostics safety, app-status
  consistency, and rollback triggers. Changing that profile invalidates prior
  immediate-promotion evidence until the affected rows are rerun.
- **FR-006g**: Controlled real-hardware validation for immediate promotion MUST
  cover built-in speakerphone far-end-only leakage, near-end-only local speech,
  double-talk, loud-speaker/clipping stress, route-change/timing stress,
  unsafe-reference negative controls, Stop/quit, diagnostics, app status, and
  rollback visibility.
- **FR-007**: The spike MUST verify candidate timing, duration, alignment,
  sample-format compatibility, route class, and confidence before candidate
  evidence can affect package readiness.
- **FR-008**: The spike MUST preserve original package truth for `mic.wav`,
  `incoming.wav`, and `manifest.json` until immediate-promotion gates pass;
  candidate or derived evidence before that point may be recorded only as
  explicitly labeled evidence.
- **FR-009**: Existing leakage finalization remains authoritative for clean,
  leakage-detected, unproven, or not-measured package status until this spike
  records an accepted immediate-promotion path across the lab-grade validation
  corpus.
- **FR-010**: The spike MUST include validation rows for built-in mic/speakers,
  built-in mic/wired headphones, USB headset, at least one browser meeting
  target, far-end-only, near-end-only, double-talk, loud speaker/clipping,
  route-change, Stop/quit, and diagnostics scenarios.
- **FR-011**: Bluetooth or AirPods-class route evidence SHOULD be collected when
  available, but missing Bluetooth evidence MUST NOT block the first built-in
  speakerphone decision and favorable Bluetooth evidence MUST NOT broaden the
  039 promotion scope.
- **FR-012**: The spike MUST record residual leakage, local speech preservation,
  double-talk confidence, reference availability, delay/timing confidence,
  clipping/dropout, route class, echo/delay metrics when available, and failure
  reason as metadata-only evidence.
- **FR-012a**: Every validation row MUST identify the acceptance-threshold
  profile used to judge it and MUST record only bounded pass/block summaries of
  thresholds, not raw audio or private content.
- **FR-013**: The spike MUST preserve visible active-capture indication,
  one-action Stop, and local app status during every validation path.
- **FR-013a**: The app MUST surface AEC3 candidate state, problem state,
  rollback state, and fallback-relevant state in user-facing status copy that is
  calm, actionable, route-scoped, and consistent with package truth.
- **FR-013b**: App statuses MUST NOT expose raw audio, transcript text, private
  meeting content, credentials, signed URLs, private local paths, or unnecessary
  technical internals.
- **FR-013c**: App statuses MUST avoid noisy alerts: normal evaluation,
  original-microphone-truth, blocked, rollback, and fallback-relevant states
  must live in the recording status surface, while interruptive attention states
  are allowed only when the user can take a clear immediate action.
- **FR-014**: The spike MUST fail closed for missing reference audio, unstable
  route topology, excessive delay, speech suppression, candidate drift, high CPU
  or memory pressure, no-hang regression, unsafe diagnostics, incomplete
  licensing review, or incomplete lineage. If immediate promotion was active,
  these same conditions MUST trigger reversible rollback to original microphone
  truth.
- **FR-015**: The spike MUST ensure diagnostics and committed evidence contain no
  raw audio, transcript text, credentials, signed URLs, private local paths, or
  private meeting content.
- **FR-016**: The spike MUST record licensing, redistribution, patent,
  packaging, signing/notarization, and release-readiness status before any AEC3
  dependency can be promoted beyond spike evidence.
- **FR-017**: The spike MUST produce a decision record that states what is
  accepted, promoted, blocked, deferred, out of scope, and whether `040`
  fallback planning remains required.
- **FR-018**: User-facing and release-facing copy MUST NOT claim clean
  speakerphone recording outside built-in Mac microphone plus built-in Mac
  speakers unless a later route-specific feature validates that route. For the
  039 route, copy MUST NOT claim clean speakerphone recording unless the accepted
  immediate-promotion outcome and existing package-readiness gates both pass.

### Key Entities

- **AEC3 Candidate**: A bounded echo-reduction candidate under evaluation, with
  route class, reference availability, lineage, timing confidence, quality
  status, licensing state, and failure state.
- **Reference Audio Evidence**: Metadata-only proof that the incoming meeting
  audio used for comparison is present, bounded, aligned, and representative of
  the speaker sound that can leak into the microphone.
- **AEC3 Validation Row**: One route/scenario combination with baseline evidence,
  candidate evidence, acceptance gates, measured outcome, and failure reason
  when applicable.
- **AEC3 Validation Corpus**: The full lab-grade evidence set required before
  immediate promotion, organized by route class, scenario family, file, slice,
  full-file run, room/device/volume condition, and pass/block reason.
- **Controlled Real-Hardware Recording Evidence**: Metadata-only proof from the
  actual app recording path on a physical Mac, showing route class, scenario
  family, package lineage, Stop behavior, candidate result, and pass/block
  reason without storing private audio or meeting content.
- **AEC3 Rollback Event**: Metadata-only evidence that a promoted candidate was
  withdrawn because route, reference, quality, timing, lineage, or diagnostics
  confidence became unsafe, returning package truth to original microphone
  evidence.
- **Derived Microphone Evidence**: Metadata-only summary of candidate microphone
  behavior, including residual leakage, speech preservation, timing confidence,
  and whether it can affect package truth.
- **App Recording Status**: The local user-facing state shown during recording
  that explains whether AEC3 is evaluating, promoted, rolled back, blocked,
  fallback-relevant, or using original microphone truth.
- **AEC3 Outcome State**: The final classification that determines whether AEC3
  can be immediately promoted, limited to derived evidence, blocked, or deferred
  to fallback.
- **Promotion Scope**: The route class where 039 may affect product behavior or
  copy. For this feature it is limited to built-in Mac microphone plus built-in
  Mac speakers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required validation rows have a recorded outcome state,
  route class, baseline comparison, candidate summary, reference-audio status,
  timing-confidence status, and metadata-only evidence.
- **SC-002**: Built-in mic plus built-in speakers is marked
  `accepted_for_immediate_promotion` only if far-end-only, near-end-only,
  double-talk, loud-speaker/clipping, route-change, alignment, Stop/quit,
  CPU/no-hang, licensing/readiness, diagnostic redaction, app-status,
  rollback-visibility, acceptance-threshold, sliced-window, and full-file gates
  all pass.
- **SC-003**: 0 accepted or promoted runs have missing or contradictory lineage
  between original microphone behavior, incoming reference audio, candidate
  microphone evidence, persisted artifacts, and manifest truth.
- **SC-004**: 0 diagnostics or committed evidence files contain raw audio,
  transcript text, credentials, signed URLs, private paths, or meeting content.
- **SC-005**: 100% of blocked or unproven outcomes include a safe reason code and
  a next-step recommendation.
- **SC-006**: 0 user-facing or release-facing notes claim clean speakerphone
  recording for the 039 route unless immediate-promotion and package-readiness
  gates both pass, and 0 notes broaden that claim beyond built-in Mac microphone
  plus built-in Mac speakers.
- **SC-007**: If AEC3 is not accepted, the final decision record names the
  specific fallback question that `040` must resolve and does not relax
  clean-recording gates.
- **SC-008**: Immediate promotion has 0 missing lab-grade corpus rows: for each
  required scenario family there are at least ten full-file validations, at
  least fifty sliced-window validations, at least two long-form full-file runs
  of 20 minutes or more, and no critical gate failures.
- **SC-009**: Immediate promotion has 0 missing room/device/volume coverage
  blockers; any absent acoustic, physical-device, or speaker-volume variation
  prevents promotion and is named in the decision record.
- **SC-010**: Immediate promotion has 100% passing controlled real-hardware app
  recording rows for far-end-only, near-end-only, double-talk,
  loud-speaker/clipping, route-change/timing, unsafe-reference, Stop/quit,
  diagnostics, app-status, and rollback scenarios, with 0 raw audio, transcript
  text, private meeting content, credentials, signed URLs, or private local
  paths in committed evidence.
- **SC-011**: 0 non-built-in route classes are marked as promoted or described as
  clean speakerphone recording by 039, even when their supporting evidence looks
  favorable.
- **SC-012**: 100% of unsafe runtime conditions after promotion produce a
  metadata-only rollback event, restore original microphone truth, and remove the
  clean-recording claim without hiding active capture or blocking Stop.
- **SC-013**: 100% of candidate, problem, rollback, and fallback-relevant states
  shown in the app match package truth, include no private content, and make it
  clear whether the app is using original microphone truth or an accepted
  promoted candidate.

## Assumptions

- `037-microphone-sample-graph-foundation`, `038-apple-voice-processing-spike`,
  and the 038 post-merge diagnostics hardening are merged before implementation
  begins.
- The first accepted decision target is built-in Mac microphone plus built-in Mac
  speakers. Other route classes support, narrow, or explain the decision but do
  not replace it.
- Non-built-in route classes require later route-specific validation before they
  can receive clean-recording product claims.
- Original `mic.wav`, `incoming.wav`, and `manifest.json` remain the default
  recording truth until this feature proves immediate promotion across the
  lab-grade validation corpus.
- Synthetic and controlled evidence can support the spike, but an accepted
  product claim requires route/scenario evidence that maps to real recording
  package behavior.
- Controlled real-hardware validation uses consented test content or synthetic
  fixtures and records only metadata evidence in repository artifacts.
- Immediate promotion is treated as a reversible route state, not a permanent
  package rewrite.
- If AEC3 cannot prove both leakage reduction and speech preservation with safe
  lineage, the default next step is `040-speakerphone-recording-fallback-decision`,
  not a relaxed clean-recording claim.
