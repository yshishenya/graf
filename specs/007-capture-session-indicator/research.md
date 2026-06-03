# Research: Manual Capture Session And Visible Indicator

## Decision: Manual Recording Is The Only Start Trigger In This Slice

**Rationale**: The constitution requires manual start/stop to remain available
and assisted auto-start is policy-sensitive. Manual start is the smallest safe
recording control surface after non-recording passthrough acceptance.

**Alternatives considered**:

- Assisted auto-start from meeting detection: rejected for this slice because it
  needs workspace policy, user acknowledgement, meeting-target detection, and
  consent gates.
- Start recording when the virtual devices receive client I/O: rejected because
  that would make route activation indistinguishable from recording start.

## Decision: App Layer Owns Recording State And Evidence

**Rationale**: The HAL driver should remain thin and realtime-safe. Recording
state, visible indicators, prerequisites, local evidence, diagnostics, and
future upload hooks are app responsibilities.

**Alternatives considered**:

- Driver-owned recording flag: rejected because it would mix product policy and
  user-visible control into the realtime audio component.
- Backend-owned recording session from the start: rejected because this slice is
  local-only and must work without upload or server availability.

## Decision: Fail Closed On Indicator Loss

**Rationale**: Invisible recording is constitutionally forbidden. If every local
visible indicator disappears, stopping or failing closed is safer than trying to
continue recording.

**Alternatives considered**:

- Continue recording and show the indicator later: rejected because it creates a
  silent/invisible recording window.
- Only log indicator failure: rejected because logging does not satisfy visible
  user control.

## Decision: Evidence Is Metadata-Only

**Rationale**: QA needs proof that recording was intentional, visible, bounded,
and stopped without exposing meeting content. Metadata-only evidence preserves
the privacy boundary and aligns with existing diagnostic redaction gates.

**Alternatives considered**:

- Store short debug audio clips: rejected because raw audio belongs to a later
  controlled recording artifact slice and would complicate deletion truth.
- Store transcript snippets: rejected because transcription is out of scope.

## Decision: Local Storage Reserve Blocks Start

**Rationale**: A recording that starts when local storage is unsafe risks silent
loss. The product must block before capture begins rather than drop frames or
misrepresent captured data.

**Alternatives considered**:

- Start and degrade after buffer failure: rejected because the failure is known
  before recording.
- Start transcript-only fallback: rejected because transcript-only mode is not
  implemented in this local manual recording slice.

## Decision: Existing Low-Resource Passthrough Remains Separate

**Rationale**: Users must be able to use working meeting audio without
recording. Recording state must not be inferred from non-recording route
activity.

**Alternatives considered**:

- Stop passthrough whenever recording stops: rejected because a user may want to
  remain in the meeting after stopping capture.
- Treat route active as recording active: rejected because it breaks the trust
  boundary established in feature 006.
