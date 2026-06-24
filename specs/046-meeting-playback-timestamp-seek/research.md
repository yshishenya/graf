# Research: Meeting Playback Timestamp Seek

## Decision 1: Playback Is Server-Mediated

**Decision**: Serve retained meeting audio through a 2brain Rec cabinet route
that reuses existing owner access, artifact policy, deletion, and audit truth.
Do not expose object-storage URLs or signed URLs to web or desktop clients.

**Rationale**: Playback touches source audio. The product already has
server-mediated artifact download and egress audit behavior; playback should
inherit that boundary rather than creating a new direct storage path.

**Alternatives considered**:

- Direct object-storage signed URLs: rejected because it broadens client egress,
  increases evidence/logging risk, and conflicts with the no signed URL
  boundary.
- Download-only playback: rejected because it does not satisfy timestamp-linked
  review and creates a clumsy MVP flow.

## Decision 2: Playback Availability Belongs In Review State

**Decision**: Extend the meeting review response with playback availability,
safe unavailable reason, route path, duration, current policy state, and speed
options.

**Rationale**: Web and desktop embedded review must agree. Putting playback in
the same review contract prevents the UI from guessing based on transcript or
download state alone.

**Alternatives considered**:

- UI-only inference from artifact rows: rejected because it can diverge across
  web and desktop, and cannot distinguish all blocked states cleanly.
- Separate playback-only discovery endpoint: rejected for MVP because meeting
  detail already owns the review state and can carry the safe metadata.

## Decision 3: Use Segment Start Seconds As Seek Targets

**Decision**: Transcript segment start times are the canonical seek targets.
Malformed, missing, negative, or out-of-range timestamps remain visible as
transcript text metadata but do not become active seek controls.

**Rationale**: Existing transcript segments already include start and end
seconds. This avoids adding a second timing model and gives deterministic test
coverage.

**Alternatives considered**:

- Diarization segment starts: rejected because transcript review is the owner
  action surface and diarization may be partial or unavailable.
- Generated word-level timing: rejected because the current pipeline does not
  prove word-level alignment and this feature should not create a new STT
  requirement.

## Decision 4: Simple MVP Player, Not Waveform

**Decision**: MVP playback uses a simple player with play/pause, current time,
duration, progress/seek, speed options, and transcript timestamp seek. Waveform
generation is outside this slice.

**Rationale**: The MVP blocker is reviewability, not waveform fidelity. A simple
player closes the PRD timestamp-linked playback gap with lower privacy and
processing risk.

**Alternatives considered**:

- Full waveform: deferred because it adds media processing and storage work.
- Track-level mixer UI: deferred because the owner needs one simple review
  playback path; track editing and mixing decisions belong to later media
  features.

## Decision 5: Dual-Track Review Audio Must Represent Both Sources

**Decision**: For normal retained dual-track meetings, the playback route must
serve one review stream that represents both microphone and incoming/system
speech sources. If the server cannot safely retrieve or build that review
stream, playback must be unavailable with a safe reason. It must not silently
play only one retained track as full meeting audio.

**Rationale**: The product goal is to verify transcript and diarization against
the source recording. Playing only the microphone or only incoming/system track
would make timestamp review misleading for half of the meeting.

**Alternatives considered**:

- Serve the first stored audio artifact: rejected because existing ordering may
  choose only one track.
- Show separate mic/system players: rejected for MVP because it makes timestamp
  review harder and contradicts the simple review-player goal.
- Add a full waveform/mixer UI: deferred because this feature only needs a
  trustworthy review stream, not editing or production-grade mixing controls.

## Decision 6: Metadata-Only Evidence

**Decision**: Validation evidence may include route state, availability,
unavailable reason, duration, current time, selected segment index, and pass/fail
counts. It must not include raw audio, transcript text, object keys, signed URLs,
credentials, private local paths, account identifiers, or private meeting
content.

**Rationale**: This matches existing Spec Kit evidence rules and keeps the
release proof safe to commit.

**Alternatives considered**:

- Screenshot evidence with visible transcript text: rejected unless synthetic
  fixture text is used and explicitly marked safe.
- Audio fixture artifacts in git: rejected because raw audio is forbidden in
  committed evidence.
