# Feature Specification: Meeting Playback Timestamp Seek

**Feature Branch**: `046-meeting-playback-timestamp-seek`

**Created**: 2026-06-24

**Status**: Implemented, merged, released, and deployed

**Input**: User description: "Finish the MVP carefully through Spec Kit, recheck the macOS app and web cabinet, and close the meeting review gap where retained audio playback must be linked to transcript timestamps."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Play Meeting Audio From Review (Priority: P1)

As a meeting owner, I want to play the retained meeting audio from the meeting review page so that I can verify the transcript against the actual source recording.

**Why this priority**: Transcript quality cannot be trusted in the MVP if the owner cannot quickly check the source audio from the same review surface.

**Independent Test**: Can be fully tested with one processed meeting that has retained audio available to the owner. The owner opens the meeting detail page, sees the player, starts playback, pauses playback, changes position, and sees truthful current time and duration.

**Acceptance Scenarios**:

1. **Given** a processed meeting with retained audio available to the owner, **When** the owner opens the meeting detail page, **Then** the page shows playback controls, duration, current time, and a truthful available state.
2. **Given** playback controls are visible, **When** the owner starts and pauses playback, **Then** the controls and current-time display update without leaving the meeting review page.
3. **Given** a meeting has transcript and diarization results, **When** audio is available, **Then** playback appears together with transcript and speaker context rather than as a disconnected download-only action.

---

### User Story 2 - Seek From Transcript Timestamps (Priority: P1)

As a meeting owner, I want to click a transcript timestamp or segment to jump playback to that moment so that review is fast and precise.

**Why this priority**: The MVP review experience should help the owner inspect uncertain transcript sections without scrubbing blindly through the whole recording.

**Independent Test**: Can be fully tested with one processed meeting containing at least three timestamped transcript segments. The owner clicks each timestamp and playback moves to the corresponding segment start.

**Acceptance Scenarios**:

1. **Given** a transcript segment has a start timestamp, **When** the owner activates that timestamp, **Then** playback seeks to the start of that segment.
2. **Given** the owner uses keyboard navigation, **When** focus reaches a timestamp and the owner activates it, **Then** the same seek behavior occurs.
3. **Given** playback is unavailable but transcript timestamps are visible, **When** the owner activates a timestamp, **Then** the interface explains why audio seeking is unavailable without hiding the transcript.

---

### User Story 3 - Respect Playback Policy And Privacy (Priority: P1)

As a privacy and security owner, I need playback to respect access, retention, deletion, and audio-availability policy so that source audio is never exposed from an unauthorized or invalid state.

**Why this priority**: Playback touches source audio and therefore must preserve the same trust boundary as upload, download, export, retention, deletion, and owner access.

**Independent Test**: Can be fully tested with meetings covering allowed, unauthorized, deleted, audio-purged, transcript-only, processing, and failed states. Only allowed retained-audio meetings expose playback.

**Acceptance Scenarios**:

1. **Given** a user is not allowed to access a meeting, **When** they try to open the review page, **Then** no playable audio state is exposed.
2. **Given** a meeting is deleted, deleting, audio-purged, transcript-only, processing, or failed, **When** the review page renders, **Then** it shows a truthful unavailable state and does not expose playback.
3. **Given** playback is unavailable for a policy reason, **When** the owner views the meeting, **Then** the reason is understandable without promising deletion or retention guarantees outside 2brain Rec control.

---

### User Story 4 - Match Web And Desktop Review (Priority: P2)

As a meeting owner using the macOS app, I want the embedded meeting review to behave like the web cabinet so that I do not have to switch surfaces to inspect audio and transcript timing.

**Why this priority**: The MVP has both a native desktop capture surface and a server-owned review cabinet. They must not contradict each other after a recording is processed.

**Independent Test**: Can be tested with the same processed meeting opened in web review and embedded desktop review. Playback availability, unavailable reasons, timestamps, and seek behavior match.

**Acceptance Scenarios**:

1. **Given** playback is available in the web cabinet, **When** the same meeting is opened from the macOS app, **Then** the embedded review shows the same playback availability and timestamp seek affordances.
2. **Given** playback is unavailable in the web cabinet, **When** the same meeting is opened from the macOS app, **Then** the embedded review shows the same truthful unavailable reason.

### Edge Cases

- Meeting has transcript timestamps but no retained or authorized audio.
- Dual-track meeting has retained microphone and incoming/system tracks, but a safe combined review stream cannot be built or retrieved.
- Meeting has retained audio but processing is still running or failed.
- Meeting has been deleted, is deleting, or has audio purged while transcript metadata remains visible.
- Owner access changes while the review page is open.
- Transcript segment has a malformed, missing, repeated, or out-of-range timestamp.
- Playback reaches the end of the retained audio.
- Network or dependency failure interrupts playback availability.
- Desktop embedded review is opened before the server has refreshed the latest processing state.
- Mobile-width web cabinet must not overlap controls, transcript rows, or unavailable-state text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST show audio playback controls on meeting review only when the current viewer is allowed to access retained meeting audio.
- **FR-002**: The system MUST show a truthful playback-unavailable state when audio is absent, purged, still processing, failed, deleted, deleting, transcript-only, unavailable as a review stream, or not allowed for the viewer.
- **FR-003**: The system MUST let an allowed owner start, pause, and seek retained meeting audio from the meeting review surface.
- **FR-004**: The system MUST display current playback time and meeting audio duration when retained audio is available.
- **FR-005**: The system MUST make transcript timestamps or segment starts activatable seek targets when playback is available.
- **FR-006**: The system MUST preserve transcript readability when playback is unavailable; unavailable playback must not hide transcript or diarization results that the viewer is allowed to see.
- **FR-007**: The system MUST keep web cabinet and desktop embedded cabinet playback availability, unavailable reasons, and timestamp seek behavior consistent for the same meeting and viewer.
- **FR-008**: The system MUST prevent playable audio exposure for unauthorized, policy-disabled, deleted, deleting, audio-purged, transcript-only, processing, failed, no-audio, and review-audio-unavailable states.
- **FR-009**: The system MUST avoid exposing raw storage paths, signed URLs, credentials, private local paths, transcript text, or meeting content in logs, diagnostics, screenshots, or metadata-only evidence for playback.
- **FR-010**: The system MUST keep deletion and retention copy truthful and must not promise erasure outside systems controlled by 2brain Rec.
- **FR-011**: The system MUST support keyboard activation for timestamp seek targets and playback controls.
- **FR-012**: The system MUST present playback controls and transcript seek targets without horizontal overflow or text overlap on desktop, embedded desktop, and mobile-width review surfaces.
- **FR-013**: The system MUST handle malformed, missing, duplicated, or out-of-range transcript timestamps without breaking the review page.
- **FR-014**: The system MUST record metadata-only evidence of playback availability and seek validation for release review.
- **FR-015**: The system MUST leave transcript editing, speaker editing, waveform generation, video playback, public links, and real echo/noise suppression outside this feature unless a later spec explicitly includes them.
- **FR-016**: For dual-track retained recordings, the playable review audio MUST represent both local microphone and incoming/system speech sources in one review stream, or show a truthful unavailable reason. The system MUST NOT silently present a single retained track as full meeting audio when both sources are required to verify the transcript.

### Key Entities *(include if feature involves data)*

- **Playback Availability**: Whether retained meeting audio can be played by the current viewer, including a user-safe unavailable reason when it cannot.
- **Playback State**: The visible current time, duration, playing or paused state, and selected position for the review session.
- **Review Audio Stream**: A server-mediated playback stream used for review. For dual-track meetings, this stream represents both local microphone and incoming/system sources.
- **Transcript Seek Target**: A timestamped transcript segment or timestamp label that can move playback to a segment start.
- **Playback Policy State**: The access, retention, deletion, audio-retention, processing, and meeting lifecycle state that controls whether audio may be played.
- **Playback Evidence**: Metadata-only proof that playback availability, blocked states, and timestamp seek behavior were validated without recording private audio or transcript content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For an allowed processed meeting with retained audio, the owner can start playback, pause playback, and seek to a selected position from the review page without leaving the page.
- **SC-002**: For at least three transcript segments in a processed meeting, activating each timestamp moves playback to the matching segment start within one second.
- **SC-003**: For unauthorized, deleted, deleting, audio-purged, transcript-only, processing, failed, no-audio, and review-audio-unavailable states, no playable audio is exposed and the review page shows a truthful unavailable state.
- **SC-004**: Web review and embedded desktop review show matching playback availability and unavailable reasons for the same meeting state.
- **SC-005**: Playback controls and timestamp seek targets are usable by keyboard and visible without overlap on desktop, embedded desktop, and mobile-width review surfaces.
- **SC-006**: Metadata-only validation evidence contains no raw audio, transcript text, credentials, signed URLs, private paths, or private meeting content.
- **SC-007**: The feature does not weaken existing access, retention, deletion, upload, transcription, or MediaScribe credential boundaries.
- **SC-008**: For a synthetic dual-track ready meeting, playback availability and playback route validation prove that the review stream is a combined review audio stream or a safe unavailable state, never an unlabeled single-track substitute.

## Assumptions

- Existing authenticated owner review and embedded desktop review surfaces remain the main MVP meeting review surfaces.
- Existing server-owned meeting result truth remains authoritative for transcript, diarization, access, retention, deletion, and audio availability.
- A simple accessible player with a progress bar is acceptable for MVP; full waveform generation is not required by this feature.
- The feature should use retained meeting audio only when policy allows it. It should not create a new external audio egress path for public or unauthorized access.
- Existing retained microphone and incoming/system track artifacts are the source of truth for review audio. If the server cannot safely build or retrieve a review stream representing the required sources, playback must fail closed with a user-safe reason.
- Real echo cancellation and noise suppression remain in feature `044` and are not required to implement timestamp-linked playback.
