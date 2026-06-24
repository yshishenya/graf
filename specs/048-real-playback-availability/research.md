# Research: Real Playback Availability

## Decision 1: Review Playback Is Not Artifact Download

**Decision**: Separate review playback from `audio_download` / export policy.
Owner review playback is allowed when the viewer can see the meeting, the
meeting is ready or partial, retained dual-track audio exists, and lifecycle
state permits playback. Download/export controls continue to use artifact
egress policy.

**Rationale**: The `046` implementation reused artifact download policy, so
real meetings with the default disabled download policy did not show the
player. Turning on `audio_download` by default would solve the visible player
but would also enable file download, which is a broader egress action than
in-page review.

**Alternatives considered**:

- Set default `audio_download="allowed"`: rejected because it grants file
  download/export-like behavior when the user only needs transcript review.
- Keep manual operator policy: rejected because the product path must work
  without invisible setup after every recording.
- Add a new persistent policy column immediately: deferred because owner review
  playback can be derived safely from access and lifecycle for MVP.

## Decision 2: Server-Mediated Range Playback

**Decision**: Playback should feel streamed to the browser by supporting
server-mediated byte ranges on the playback route. The route remains relative
to 2brain Rec and never returns object-storage URLs or signed URLs.

**Rationale**: Browser audio controls and seeking work best when the server
supports range requests. A range-capable server route gives the user a streaming
experience while preserving access, deletion, and audit boundaries.

**Alternatives considered**:

- Direct object storage signed URL: rejected because it broadens egress,
  complicates deletion/audit truth, and is harder to keep out of evidence.
- Forced full-file download before playback: rejected because it is slow,
  visible to users, and not a good transcript-review experience.
- Native desktop playback only: rejected for this slice because web and
  embedded desktop must stay consistent and server-owned.

## Decision 3: Clean-Room Krisp-Like Review Pattern

**Decision**: Use the user's Krisp screenshot as interaction reference only:
meeting title and actions at top, transcript as the main content, timestamps as
seek controls, and a persistent bottom playback/timeline area.

**Rationale**: The reference solves the same user problem: quickly verifying
transcript against audio. The pattern is useful, but the implementation must
use 2brain Rec's own colors, copy, layout constraints, and components.

**Alternatives considered**:

- Copy Krisp visual details: rejected by clean-room and brand-distance gates.
- Keep a plain native `<audio>` block in the page: rejected because it is easy
  to miss and does not match the desired review workflow.

## Decision 4: Speaker Timeline Uses Segment Timing

**Decision**: Speaker lanes should render visible segments based on diarization
segment start/end times and the meeting duration. The percentage remains useful
as a summary label, but it is not enough for timeline review.

**Rationale**: The user needs to inspect where speakers appear during playback.
The current lane-fill percentage only shows total talk-time share, not where in
the recording each speaker speaks.

**Alternatives considered**:

- Use one filled percentage bar per speaker: rejected because it does not
  support timeline inspection.
- Generate waveform: deferred because waveform generation adds media processing
  and storage scope beyond this playback-availability fix.

## Decision 5: Metadata-Only Evidence

**Decision**: Validation evidence may include route status codes, range header
presence, playback availability booleans, unavailable reason, duration,
selected safe segment index, observed seek position, viewport class, and
pass/fail counts. It must not include raw audio, private transcript text,
object keys, signed URLs, credentials, private paths, or account identifiers.

**Rationale**: Playback touches retained audio and transcript review. Evidence
must prove behavior without leaking the content being protected.

**Alternatives considered**:

- Commit screenshots of real private review pages: rejected because they may
  expose transcript text or meeting title.
- Commit sample audio fixtures: rejected because raw audio is forbidden in
  Spec Kit evidence.
