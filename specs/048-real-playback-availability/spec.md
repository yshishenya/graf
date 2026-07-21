# Feature Specification: Real Playback Availability

**Feature Branch**: `048-real-playback-availability`

**Created**: 2026-06-24

**Status**: Implemented, merged, released, and deployed

**Input**: User description: "Playback must be visible and useful in the real product, not only in fixtures. Use Krisp as a clean-room UX reference: transcript stays central, playback is a persistent bottom control, timestamps seek audio, speaker activity is visible on a timeline, and web plus macOS embedded review must match. Determine whether playback should stream or download and implement carefully through Spec Kit."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real Recording Shows Playback (Priority: P1)

As a meeting owner, I want a processed real recording to show audio playback in the meeting review page without an operator manually enabling an artifact-download policy, so that I can immediately verify transcript quality against source audio.

**Why this priority**: Feature `046` added playback plumbing, but real product users do not see it because playback availability is coupled to download policy. The MVP is not credible until the default owner review path exposes playback for retained, processed recordings.

**Independent Test**: Can be fully tested with a normal owner recording that uploads microphone and incoming/system tracks, finalizes, imports transcript/diarization results, and opens the review page. The owner sees the player and timestamp seek controls without manually setting `audio_download=allowed`.

**Acceptance Scenarios**:

1. **Given** an owner has a processed meeting with retained microphone and incoming/system audio, **When** the owner opens web meeting review, **Then** playback is available, the player points to a server-owned playback route, and transcript timestamps are seekable.
2. **Given** the same meeting is opened inside the macOS embedded cabinet, **When** the review loads, **Then** playback availability, timestamp seek controls, and unavailable reasons match the web review.
3. **Given** audio download/export policy remains disabled, **When** the owner opens meeting review, **Then** review playback is still available while the file download/export controls remain disabled or policy-blocked.

---

### User Story 2 - Playback Feels Like Review, Not Download (Priority: P1)

As a meeting owner, I want playback to behave like an in-page review player with timeline, seeking, and speaker context, so that I can inspect transcript quality quickly without downloading audio files.

**Why this priority**: The desired product experience is closer to Krisp's review screen: transcript in the main area, persistent player at the bottom, time markers as seek targets, and speaker activity visible in the player area. A plain HTML audio block buried in the page is not enough for MVP review.

**Independent Test**: Can be tested with fixture-backed web and embedded review pages at desktop and mobile widths. The page has a persistent bottom playback bar, no horizontal overflow, timestamp seek works, and speaker lanes are visible when diarization is available.

**Acceptance Scenarios**:

1. **Given** playback is available, **When** the meeting detail page renders, **Then** the player is presented as a persistent bottom review bar with play/pause, skip back, skip forward, current time, duration, speed, and source-state copy.
2. **Given** transcript segments have valid timestamps, **When** the owner activates a timestamp, **Then** playback seeks to that segment and starts without leaving the page.
3. **Given** diarization is available, **When** the review page renders, **Then** speaker lanes show visible activity across the meeting duration and remain aligned with the overall player duration.
4. **Given** playback is unavailable, **When** the review page renders, **Then** the bottom review area shows a clear unavailable state and the transcript remains readable.

---

### User Story 3 - Stream Safely Without Public Audio Egress (Priority: P1)

As a privacy and security owner, I need playback to use server-mediated streaming semantics rather than public signed URLs or direct storage links, so that source audio stays inside 2brain Rec access, deletion, retention, and audit controls.

**Why this priority**: Playback touches retained source audio. It must feel instant and seekable to the user while preserving the same trust boundary as upload, processing, access, deletion, and metadata-only evidence.

**Independent Test**: Can be tested through the playback route contract. Range requests return partial audio with safe headers, direct object-storage identifiers never appear in responses, and denied states fail closed without exposing existence or private storage details.

**Acceptance Scenarios**:

1. **Given** playback is available, **When** the browser requests the playback route with a byte range, **Then** the server returns a partial audio response suitable for seeking and includes safe range headers.
2. **Given** playback is available, **When** the review page loads, **Then** the browser can start playback through the server-owned route without receiving a signed URL, object key, or storage path.
3. **Given** the viewer is unauthorized, the meeting is deleting/deleted, audio is missing/purged, processing failed, or a safe review stream cannot be produced, **When** playback is requested, **Then** the server fails closed with safe metadata-only audit and no playable audio.

---

### User Story 4 - Preserve Product Truth And Operations (Priority: P2)

As an operator, I want status documents, release notes, and evidence to state exactly what playback does and does not prove, so that release decisions do not confuse fixture validation with real product readiness.

**Why this priority**: The `046` documentation overclaimed product-visible playback in some places while older status text still said it was not shipped. The MVP needs one truthful source of status.

**Independent Test**: Can be tested by reviewing changelog, current-product-status, validation evidence, and GitHub issue/PR closure text. They must describe owner review playback, server-mediated streaming, web/embedded parity, and known limitations in simple Russian.

**Acceptance Scenarios**:

1. **Given** implementation validation is complete, **When** status docs are reviewed, **Then** they no longer claim fixture-only evidence as full real-product playback.
2. **Given** release notes are prepared, **When** a non-engineer reads them, **Then** the text explains that processed recordings can be listened to in review, downloads remain separate, and echo/noise cleanup remains separate work.

### Edge Cases

- A ready meeting has transcript and diarization but only one retained audio source.
- A ready meeting has both retained sources but the server cannot produce safe review audio.
- A viewer can view a meeting through team or share access but download/export is disabled.
- A meeting is processing, failed, blocked, deleted, deleting, audio-purged, or transcript-only.
- Browser range request is malformed, out of bounds, suffix-only, or open-ended.
- Playback starts before metadata duration is loaded.
- Transcript segment timestamp is missing, repeated, negative, or beyond playback duration.
- Mobile-width review must not hide playback controls or overlap transcript text.
- Embedded macOS review must use the same server-owned route and not add a separate desktop audio egress path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST make review playback available by default for the meeting owner when a processed meeting has retained microphone and incoming/system audio, transcript or diarization review content, and no deletion or processing blocker.
- **FR-002**: The system MUST NOT require `audio_download=allowed` or any manual artifact-download policy override for owner review playback.
- **FR-003**: The system MUST keep audio file download/export policy separate from in-page review playback. Enabling review playback MUST NOT automatically enable "Download audio" or export controls.
- **FR-004**: The system MUST expose playback through a server-owned relative playback route, not through object-storage URLs, signed URLs, local file paths, or direct storage identifiers.
- **FR-005**: The system MUST support browser seeking through server-mediated streaming semantics, including safe byte-range responses for available playback.
- **FR-006**: The system MUST include both retained microphone and incoming/system speech sources in the review playback stream, or show a truthful unavailable state. It MUST NOT silently present a single retained track as full meeting playback for normal dual-track recordings.
- **FR-007**: The system MUST fail closed for unauthorized, deleted, deleting, audio-purged, transcript-only, processing, failed, missing-source, storage-unavailable, or unsafe-review-audio states.
- **FR-008**: The system MUST render a persistent bottom review player when playback is available, with play/pause, skip backward, skip forward, current time, duration, speed, and source-state copy.
- **FR-009**: The system MUST render transcript timestamps as seek controls only when playback is available and each timestamp is valid for the playback duration.
- **FR-010**: The system MUST render speaker activity lanes when diarization is available, using meeting duration and segment timing to show where each speaker appears.
- **FR-011**: The system MUST keep web review and macOS embedded review consistent for playback availability, unavailable reasons, timestamp seek behavior, and player layout.
- **FR-012**: The system MUST preserve transcript readability when playback is unavailable; unavailable playback must not hide transcript or diarization content that the viewer may see.
- **FR-013**: The system MUST record metadata-only audit/evidence for allowed and denied playback without raw audio, transcript text, credentials, signed URLs, storage object keys, private local paths, or private meeting content.
- **FR-014**: The system MUST keep release/status text truthful in simple Russian, distinguishing real owner review playback from downloads, exports, echo/noise suppression, waveform generation, transcript editing, and final user rollout readiness.

### Key Entities *(include if feature involves data)*

- **Review Playback Availability**: User-facing state that determines whether the meeting review page can play retained audio for transcript verification.
- **Review Playback Stream**: Server-mediated playback response used by browser and embedded desktop review; it is not a public file URL and not the same as "Download audio".
- **Playback Range Request**: A browser request for a byte range of review audio, used for fast start and seeking.
- **Speaker Activity Lane**: A compact visual timeline of diarized speaker segments across the meeting duration.
- **Playback Evidence**: Metadata-only proof of playback availability, blocked states, UI behavior, and range semantics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a normal owner processed recording with retained microphone and incoming/system audio, review playback is available in web and embedded macOS review without manually enabling artifact-download policy.
- **SC-002**: The same meeting keeps audio download/export controls disabled when those policies are disabled, proving review playback and downloads are separate.
- **SC-003**: Activating at least three transcript timestamps moves playback to the matching segment start within one second in browser runtime validation.
- **SC-004**: Available playback route responses support byte-range seeking and do not expose signed URLs, object keys, local paths, credentials, raw transcript text, or private meeting content.
- **SC-005**: Blocked playback states expose no playable audio for unauthorized, deleted/deleting, processing, failed, missing-source, storage-unavailable, and unsafe-review-audio cases.
- **SC-006**: Desktop-width, mobile-width, and macOS embedded review pages show no horizontal overflow or incoherent overlap in the transcript, player, and speaker timeline.
- **SC-007**: Status docs, changelog, and release notes explain in simple Russian that the user can listen to processed recordings in review, that downloads remain separate, and that echo/noise suppression remains outside this slice.

## Assumptions

- Krisp is used as a clean-room product reference for interaction pattern only: transcript-first review, persistent bottom player, seekable timestamps, and speaker timeline. No proprietary Krisp code, copy, icons, or assets are reused.
- MVP playback should feel streaming/seeking to the user. Technically, it should use server-mediated playback with safe range support rather than direct download links.
- Existing retained `mic.wav` and `incoming.wav` artifacts remain the source inputs for review playback.
- This slice does not implement waveform generation, transcript editing, speaker reassignment, native Swift audio playback, public links, real echo cancellation, or noise suppression.
- The macOS app's embedded cabinet remains server-owned HTML for this slice; separate native playback controls can be considered later only if the server-owned surface proves insufficient.
