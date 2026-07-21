# Feature Specification: Apple Voice Processing Spike

**Feature Branch**: `038-apple-voice-processing-spike`

**Created**: 2026-06-22

**Status**: Archived Apple voice-processing spike; not a current runtime candidate

**Input**: User description: "Continue the clean-recording work after 037 and evaluate Apple voice processing before moving to WebRTC AEC3."

## Program Context

Features `037`-`041` are the clean-recording chain from
`docs/audio-capture-backlog.md`. Feature `037` is merged and gives 2brain Rec an
app-owned microphone sample graph for recording. This specification activates
only feature `038`: a bounded Apple native voice-processing spike for reducing
built-in speaker-to-mic leakage.

This feature must answer whether Apple native processing can become a truthful
route toward clean built-in speakerphone recording. It must not treat the
availability of an Apple API, a system Mic Mode, or a processed internal test
recording as proof that 2brain Rec can claim clean dual-track recording.

Follow-up slices remain separate:

- `039-webrtc-aec3-speakerphone-spike`
- `040-speakerphone-recording-fallback-decision`
- `041-recording-permission-readiness-onboarding`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classify Apple Processing Feasibility For Built-In Speakerphone (Priority: P1)

As a product owner, I need a clear go/no-go classification for Apple native
voice processing on built-in Mac microphone plus built-in Mac speakers, so the
product does not promise clean speakerphone recording without evidence.

**Why this priority**: Built-in speakerphone is the most tempting user promise
and the highest risk for false clean recordings. Apple processing is the
lowest-maintenance candidate if it works, but only evidence can decide that.

**Independent Test**: Run the bounded Apple processing validation matrix on the
built-in mic/speaker route and record one of the accepted spike outcomes with
metadata-only evidence, baseline comparison, and explicit limitations.

**Acceptance Scenarios**:

1. **Given** a merged app-owned microphone graph from `037`, **When** Apple
   native voice processing is evaluated on built-in mic plus built-in speakers,
   **Then** the spike records whether the route is accepted, blocked, guidance
   only, or deferred without making a clean recording claim unless all gates
   pass.
2. **Given** remote speaker audio is playing and the local user is silent,
   **When** the processed microphone evidence is compared with the unprocessed
   baseline, **Then** the result records residual leakage, confidence, and
   whether final package truth can be clean.
3. **Given** local speech and remote audio overlap, **When** Apple processing is
   evaluated during double-talk, **Then** the result records whether local
   speech remains preserved rather than being muted or heavily damaged.

---

### User Story 2 - Prove Processed Signal Lineage Matches Product Truth (Priority: P1)

As an engineering owner, I need to know whether the same processed near-end
signal can feed the meeting microphone path and persisted `mic.wav`, so live
behavior and saved recording truth do not diverge.

**Why this priority**: Apple processing is not useful for the product if it only
cleans an internal test recorder, a user-controlled system mode, or a different
capture path than the one persisted in the package.

**Independent Test**: Produce a controlled recording package with processed
candidate evidence and verify whether the processed near-end signal is traceable
to the live microphone path, the persisted microphone artifact, the incoming
reference artifact, and the manifest.

**Acceptance Scenarios**:

1. **Given** Apple processing appears available, **When** a recording package is
   finalized, **Then** the manifest distinguishes original, processed,
   guidance-only, unproven, and blocked evidence without overwriting original
   package truth.
2. **Given** processed microphone evidence exists, **When** `mic.wav` and
   `incoming.wav` are inspected, **Then** the package records whether alignment,
   duration, sample format, channel count, and timing confidence remain within
   accepted recording tolerances.
3. **Given** Apple processing cannot see the same far-end output that reaches
   the speakers, **When** validation completes, **Then** the route is classified
   as blocked or guidance-only rather than accepted.

---

### User Story 3 - Keep Failures Safe, Visible, And Metadata-Only (Priority: P1)

As a privacy and capture-safety owner, I need every Apple processing failure to
fail closed with visible recording controls and metadata-only diagnostics, so a
spike cannot hide capture, leak private content, or mark uncertain audio clean.

**Why this priority**: This feature touches live microphone processing and route
truth. Any crash, hang, route change, or uncertain result must be safer than a
false acceptance.

**Independent Test**: Exercise permission failure, route change, missing far-end
reference, unsupported Mic Mode, noisy/clipped speakers, app stop, and app quit
while Apple processing evidence is active. Confirm each case has a bounded
state, visible control behavior, and metadata-only diagnostics.

**Acceptance Scenarios**:

1. **Given** Apple processing cannot start, changes route topology, or becomes
   unavailable during capture, **When** recording continues or stops, **Then**
   the product records a blocked or unproven state and preserves one-action Stop.
2. **Given** diagnostics are exported after any spike result, **When** evidence
   is inspected, **Then** it contains only bounded counters, route classes,
   status fields, reason codes, and threshold summaries.
3. **Given** the user changes microphone, output, volume, or system Mic Mode,
   **When** validation completes, **Then** the result states whether the change
   invalidated, narrowed, or preserved the Apple processing conclusion.

---

### User Story 4 - Decide The Next Clean-Recording Step (Priority: P2)

As a product and technical owner, I need the spike to produce a decision record
that tells us whether to promote Apple processing, use it only as guidance, or
move to WebRTC AEC3/fallback planning.

**Why this priority**: The next expensive branch should be chosen from evidence,
not intuition. A blocked Apple result is still useful if it cleanly justifies
`039` or `040`.

**Independent Test**: Review the completed spike evidence and confirm it maps to
exactly one primary outcome state with follow-up recommendations and no
contradictory product claim.

**Acceptance Scenarios**:

1. **Given** all required validation rows are complete, **When** the spike is
   summarized, **Then** exactly one primary outcome state is selected and linked
   to supporting evidence.
2. **Given** Apple processing is not accepted for built-in speakerphone, **When**
   the decision record is published, **Then** it identifies whether the next
   step is WebRTC AEC3, guidance-only UX, headset-first acceptance, or fallback
   decision work.

### Edge Cases

- Apple processing is available for input but not for the output reference.
- Apple processing changes sample rate, channel count, sample format, channel
  order, gain behavior, or route topology.
- The processed near-end signal is observable internally but cannot feed the
  persisted microphone artifact.
- System Mic Mode or Voice Isolation can be observed or opened for the user but
  not controlled deterministically by 2brain Rec.
- The far-end speaker reference is late, absent, protected, silent, clipped, or
  different from the signal reaching physical speakers.
- The route changes before recording, during recording, between validation
  intervals, or after app wake.
- The user uses wired headphones, USB headset, Bluetooth, AirPods-class routes,
  or an external display/output route.
- Double-talk causes near-end speech suppression, half-duplex behavior, or
  inconsistent gain.
- CPU, latency, no-hang, Stop, quit, or resource-release behavior regresses.
- Diagnostics, evidence files, or decision records accidentally include raw
  audio, transcript text, credentials, signed URLs, private file paths, or
  meeting content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The spike MUST evaluate Apple native voice processing only after
  the app-owned microphone graph from `037` is available in the recording path.
- **FR-002**: The spike MUST classify Apple processing with one primary outcome:
  `accepted_for_builtin_speakerphone`, `accepted_for_guidance_only`,
  `accepted_for_headset_routes_only`, `blocked_route_topology`,
  `blocked_quality`, `blocked_stability`, or `defer_to_webrtc_aec3`.
- **FR-003**: The spike MUST compare processed microphone evidence against an
  unprocessed baseline for the same route class and validation scenario.
- **FR-004**: The spike MUST verify whether the processed near-end signal can
  feed both the live microphone path and the persisted microphone artifact before
  any acceptance state can mention clean recording.
- **FR-005**: The spike MUST preserve original package truth for `mic.wav`,
  `incoming.wav`, and `manifest.json`; processed evidence may be recorded only
  as traceable candidate or derived evidence unless a later spec changes
  artifact semantics.
- **FR-006**: The spike MUST keep existing leakage finalization as the authority
  for clean, leakage-detected, unproven, or not-measured package status.
- **FR-007**: The spike MUST include validation rows for built-in mic/speakers,
  built-in mic/wired headphones, USB headset, at least one browser meeting
  target, far-end-only, near-end-only, double-talk, loud speaker/clipping, and
  route-change scenarios.
- **FR-008**: Bluetooth or AirPods-class route evidence SHOULD be collected when
  available, but missing Bluetooth evidence MUST NOT block the initial built-in
  speakerphone decision.
- **FR-009**: The spike MUST record whether Apple processing sees the same
  far-end output that reaches the physical speakers.
- **FR-010**: The spike MUST record whether `mic.wav` and `incoming.wav` remain
  aligned within the accepted recording tolerance for each candidate run.
- **FR-011**: The spike MUST record sample format, channel count, route class,
  timing confidence, local speech preservation, residual leakage, clipping, and
  double-talk confidence as metadata-only evidence.
- **FR-012**: The spike MUST fail closed when Apple processing is unavailable,
  route-dependent, user/system-controlled, missing a valid far-end reference,
  unstable, or unable to preserve local speech.
- **FR-013**: The spike MUST preserve visible active-capture indication and
  one-action Stop during every validation path.
- **FR-014**: The spike MUST avoid hidden system setting changes; user/system Mic
  Mode states may be observed or guided only when the evidence labels them as
  user/system controlled.
- **FR-015**: The spike MUST ensure diagnostics and committed evidence contain
  no raw audio, transcript text, credentials, signed URLs, private local paths,
  or private meeting content.
- **FR-016**: The spike MUST produce a decision record that states what is
  accepted, blocked, deferred, and out of scope for `039` and `040`.

### Key Entities

- **Apple Processing Candidate**: A bounded processing path under evaluation,
  with route class, ownership proof, reference availability, output lineage, and
  stability status.
- **Validation Row**: One route/scenario combination with baseline evidence,
  processed evidence, expected gates, measured outcome, and failure reason when
  applicable.
- **Processed Microphone Evidence**: Metadata-only summary of processed near-end
  behavior, including residual leakage, speech preservation, timing confidence,
  and whether it can affect package truth.
- **Spike Outcome State**: The final classification that determines whether
  Apple processing can be promoted, narrowed, used only as guidance, blocked, or
  deferred to WebRTC AEC3.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of required validation rows have a recorded outcome state,
  route class, baseline comparison, and metadata-only evidence summary.
- **SC-002**: Built-in mic plus built-in speakers is marked
  `accepted_for_builtin_speakerphone` only if far-end-only, near-end-only,
  double-talk, loud speaker, route-change, alignment, Stop/quit, and diagnostic
  redaction gates all pass.
- **SC-003**: 0 accepted runs have missing or contradictory lineage between live
  microphone behavior, persisted microphone artifact, incoming reference, and
  manifest truth.
- **SC-004**: 0 diagnostics or committed evidence files contain raw audio,
  transcript text, credentials, signed URLs, private paths, or meeting content.
- **SC-005**: 100% of blocked or unproven outcomes include a safe reason code and
  a next-step recommendation.
- **SC-006**: 0 user-facing or release-facing notes claim clean speakerphone
  recording unless the accepted built-in speakerphone state and existing leakage
  finalization gates both pass.

## Assumptions

- `037-microphone-sample-graph-foundation` is merged before implementation of
  this feature begins.
- The first accepted decision target is built-in Mac microphone plus built-in Mac
  speakers; other route classes can narrow or support the decision but do not
  replace it.
- Existing `020` leakage finalization and `025`/`037` package contracts remain
  authoritative until a later spec explicitly changes them.
- This spike may use synthetic, controlled, and manual runtime evidence, but all
  committed evidence must remain metadata-only.
- If Apple processing cannot prove both signal lineage and quality, the default
  next step is `039-webrtc-aec3-speakerphone-spike` or `040` fallback decision,
  not a relaxed clean-recording claim.
