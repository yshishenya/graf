# Feature Specification: Interactive Playback Timeline

**Feature Branch**: `118-interactive-playback-timeline`

**Created**: 2026-07-21

**Status**: Implemented, merged through PR #3944, and released as `v2026.07.21.4`; separate production rollout proof is not claimed

**Input**: User description: "Связать ползунок проигрывателя с таймлайном спикеров, сделать speaker timeline кликабельным, подсвечивать говорящего, переходить к нужному тексту и позволить вручную задавать имена спикеров."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seek on one shared timeline (Priority: P1)

As a meeting reviewer, I can seek from either the main playback control or any speaker lane and land at the same recording time, so the visual position never points to different audio.

**Why this priority**: Incorrect time mapping breaks trust in every playback and review action.

**Independent Test**: On a retained recording with speaker lanes, seeking to the same horizontal position from the main control and a speaker lane lands within 0.25 seconds of the same playback time.

**Acceptance Scenarios**:

1. **Given** playback and speaker lanes are available, **When** the reviewer seeks to a horizontal position in either surface, **Then** both surfaces show one aligned playhead and playback uses the corresponding recording time.
2. **Given** the reviewer clicks a speech segment or an empty part of a speaker lane, **When** the click is accepted, **Then** playback seeks to the exact bounded time represented by that position.
3. **Given** the user navigates with a keyboard, **When** the shared seek control receives focus, **Then** standard keyboard seeking remains available and the current time is announced accessibly.

---

### User Story 2 - Follow the active speaker and transcript (Priority: P2)

As a meeting reviewer, I can see who is speaking and automatically reach the corresponding transcript turn after seeking, so I can connect audio, speaker, and text without manual searching.

**Why this priority**: The timeline becomes useful for review only when current audio context is visible in both the speaker lanes and transcript.

**Independent Test**: Seeking into known speaker intervals highlights every active lane and centers the matching transcript turn; normal playback updates the same states as time advances.

**Acceptance Scenarios**:

1. **Given** playback time falls inside one or more speaker intervals, **When** playback advances or seeks, **Then** each matching speaker lane is visibly active and non-matching lanes are not.
2. **Given** a seek originates from the shared playback timeline or a transcript timestamp, **When** the target time is applied, **Then** the matching transcript turn is centered in the visible transcript area and receives a temporary current-turn state.
3. **Given** the target time falls in a silence gap, **When** the reviewer seeks, **Then** playback stays at the exact requested time and the nearest preceding transcript turn is centered; before the first turn, the first turn is centered.
4. **Given** reduced-motion preferences are enabled, **When** transcript following occurs, **Then** centering happens without animated scrolling.

---

### User Story 3 - Name speakers manually (Priority: P3)

As an authorized meeting editor, I can replace an automatic speaker label with a readable name and see it consistently in the timeline and transcript after reload.

**Why this priority**: Human names make later review understandable, while playback correctness remains useful without them.

**Independent Test**: Rename one speaker, reload the meeting, and verify the saved name appears on every turn and lane for that speaker while other speakers remain unchanged.

**Acceptance Scenarios**:

1. **Given** the reviewer is the meeting creator or a workspace owner/admin, **When** they submit a valid speaker name, **Then** the name is saved for that meeting and applied to all matching timeline lanes and transcript turns.
2. **Given** the reviewer only has viewing access, **When** they open the meeting, **Then** saved names are visible but rename controls are unavailable.
3. **Given** an authorized editor submits an empty name, **When** the change is saved, **Then** the manual name is removed and the canonical automatic label is restored.
4. **Given** saving fails, **When** the editor submits a name, **Then** the current visible label remains unchanged and a concise retryable error is shown without exposing meeting content.

### Edge Cases

- Playback duration can differ slightly from the last transcript or diarization timestamp; every visual and seek position is bounded to the playable duration.
- Speaker intervals can overlap; all lanes active at the current time are highlighted.
- A meeting can have playback without diarization or transcript; the normal playback control remains usable and absent review surfaces do not create inactive controls.
- A meeting can have diarization but unavailable audio; labels remain readable and renameable for authorized editors, but no seek interaction is presented.
- Very short speaker intervals remain selectable without changing their truthful start and end times.
- Speaker names containing only whitespace, control characters, markup, or more than 80 characters are rejected at the input boundary.
- Concurrent renames use the last successfully accepted value and every accepted change is attributable to its actor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main playback progress surface and every speaker lane MUST use identical horizontal start, end, and duration semantics.
- **FR-002**: The review surface MUST present one playhead position shared visually by the main playback control and all speaker lanes.
- **FR-003**: Reviewers MUST be able to seek by pointer from the main progress surface and from the full width of any available speaker lane, including gaps between speech intervals.
- **FR-004**: Every accepted seek target MUST be clamped to the playable interval and MUST differ by no more than 0.25 seconds between equivalent horizontal positions on the main control and speaker lanes.
- **FR-005**: Standard keyboard operation, visible focus, accessible names, and current-time announcements MUST remain available for the shared seek interaction.
- **FR-006**: The review surface MUST mark every speaker lane whose interval contains the current playback time and MUST clear stale active states as time advances, pauses, ends, or seeks.
- **FR-007**: Speaker-lane active state MUST remain distinguishable without relying on color alone and MUST meet the product's visible focus and contrast requirements.
- **FR-008**: A seek from the shared timeline or a transcript timestamp MUST center the deterministic matching transcript turn and mark it as current.
- **FR-009**: Transcript following MUST honor reduced-motion preferences and MUST NOT continuously steal focus during ordinary playback.
- **FR-010**: The review surface MUST use canonical speaker-turn timing as the link among audio time, lane activity, and transcript positioning.
- **FR-011**: The meeting creator and active workspace owners/admins MUST be able to set or clear one display name for each canonical speaker within a meeting.
- **FR-012**: View-only users MUST see saved speaker names but MUST NOT receive a rename control or mutation capability.
- **FR-013**: A saved speaker display name MUST appear consistently in transcript turns, the playback timeline, and the speaker summary for that meeting after reload.
- **FR-014**: Speaker names MUST be trimmed, limited to 80 visible characters, and reject control characters or unsafe markup at the server trust boundary.
- **FR-015**: Clearing a manual name MUST restore the canonical automatic label without changing transcript text, speaker timing, source role, or provider-originated diarization data.
- **FR-016**: Every accepted speaker-name change MUST record workspace, meeting, speaker key, actor, time, and whether the action set or cleared a name; audit data MUST NOT contain transcript or audio content.
- **FR-017**: Speaker-name records MUST participate in whole-meeting deletion and MUST NOT outlive the meeting they describe.
- **FR-018**: Rename failures MUST preserve the last confirmed name and present a safe retryable error.
- **FR-019**: Desktop-embedded and browser meeting-detail surfaces MUST expose the same playback, transcript-following, authorization, and rename behavior.
- **FR-020**: The implementation MUST reuse the existing player, canonical speaker turns, session authorization, CSRF protection, and GRAF design system without adding a second playback or identity system.

### Key Entities

- **Canonical speaker**: A meeting-scoped speaker key derived from accepted diarization, with its automatic label, source roles, talk intervals, and transcript turns.
- **Speaker display name**: An optional meeting-scoped override for one canonical speaker, including the editor and update time; it changes display only.
- **Playback position**: One bounded point on the retained recording timeline shared by the main control, speaker lanes, and transcript following.
- **Speaker-name audit event**: Metadata-only evidence of a set or clear action, linked to workspace, meeting, speaker key, and actor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Equivalent clicks at 0%, 25%, 50%, 75%, and 100% of the main progress surface and any speaker lane resolve within 0.25 seconds of the same playback time.
- **SC-002**: For a fixture containing single-speaker, overlapping-speaker, and silence intervals, 100% of sampled playback positions show the expected active lane set.
- **SC-003**: After every tested seek origin, the correct transcript turn is visible and centered within one second without moving keyboard focus unexpectedly.
- **SC-004**: An authorized editor can set, replace, clear, and verify a speaker name after reload in under 30 seconds per action.
- **SC-005**: 100% of tested unauthorized rename attempts are rejected without changing saved labels or revealing whether inaccessible meetings or speakers exist.
- **SC-006**: The meeting detail remains usable at supported desktop widths, including embedded mode, with no horizontal mismatch between the main timeline and speaker tracks.
- **SC-007**: Automated accessibility checks and keyboard review find no new critical issues in the player, timeline, transcript-following, or rename controls.

## Assumptions

- Playback, transcript, and diarization timestamps already refer to the same canonical recording timeline; this feature aligns and exposes that existing truth rather than applying an audio offset.
- Speaker names are meeting-local display overrides, not reusable contacts or cross-meeting identity matches.
- Speaker merge, split, transcript text editing, participant-name suggestions, and automatic identity matching remain out of scope.
- The existing retained playback artifact, canonical speaker-turn contract, authenticated meeting access, and deletion cascade are available dependencies.
- Russian is the current cabinet UI language; this slice keeps existing locale behavior and avoids introducing a separate localization system.
