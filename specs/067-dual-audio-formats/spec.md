# Feature Specification: Dual Audio Formats

**Feature Branch**: `067-dual-audio-formats`

**Created**: 2026-06-27

**Status**: Locally validated

**Input**: User description: "оставляем два файла WAV для транскрибации, но для playback и распространения пишем отдельный оптимальный формат/кодек/битрейт"

## Clarifications

### 2026-06-28

- The transcription contract stays unchanged: `mic.wav` and `incoming.wav` are
  the authoritative MediaScribe source files.
- The first playback/distribution artifact is a single optional local
  `meeting-review.m4a` derivative using M4A/AAC-LC. It is not a replacement for
  the transcription WAV pair.
- Review playback and audio download/export remain separate policy decisions.
  The server may use the same stored M4A bytes for both only after the caller
  passes the relevant playback or export/download policy gate.
- Invalid, partial, or wrong-container local `meeting-review.m4a` files must be
  ignored by desktop upload discovery instead of becoming server-visible
  playback artifacts.

## Product Thesis

The current recording package already has the right transcription truth:
`mic.wav` and `incoming.wav` are separate, aligned, MediaScribe-ready source
tracks. This feature must preserve that contract. The product should not replace
the transcription path with a compressed or mixed file.

The missing product layer is a separate playback and distribution asset for the
same recording. That asset should be smaller, seekable, compatible with web and
macOS review, and pleasant enough for meeting review or approved sharing. It is
derived from the best accepted capture source available, but it never becomes
the normal MediaScribe submission source.

"Higher quality than WAV" in this feature means higher perceived review quality
than the current 16 kHz mono mixed WAV playback path. A compressed derivative
cannot create fidelity that was not captured. If only the 16 kHz transcription
WAV pair is available, the playback file can improve size, seeking, and
distribution, but not true source fidelity. Real listening-quality improvement
requires using capture-rate audio before transcription downsampling or another
validated higher-fidelity source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve The Two WAV Files For Transcription (Priority: P1)

As a meeting owner, I want the product to keep `mic.wav` and `incoming.wav` as
the transcription source, so that transcript quality, source-role separation,
and timestamp alignment stay stable.

**Why this priority**: Transcription is the core downstream value. A smaller or
more convenient playback file is not acceptable if it damages source separation,
silence, padding, timestamps, or MediaScribe compatibility.

**Independent Test**: Complete a normal accepted recording and process it
through the server-owned transcription path. Confirm that the transcription
submission uses the separate microphone and incoming/system WAV sources, not the
mixed playback/distribution asset.

**Acceptance Scenarios**:

1. **Given** a recording has accepted microphone and incoming/system audio,
   **When** local custody finalizes, **Then** the recording package retains the
   required `mic.wav` and `incoming.wav` files for transcription.
2. **Given** transcription processing starts, **When** the server prepares the
   MediaScribe request, **Then** it submits separate microphone and incoming
   source files with continuous timeline truth.
3. **Given** one WAV source is missing, corrupted, silent beyond the accepted
   policy, or timeline-misaligned, **When** processing runs, **Then** the product
   blocks or degrades transcription truthfully and does not substitute one mixed
   playback file.

---

### User Story 2 - Write One Optimized Playback And Distribution Asset (Priority: P1)

As a meeting owner, I want one additional review audio file that starts quickly,
seeks smoothly, sounds comfortable, and is small enough for approved sharing, so
that I do not need to listen to or distribute a large WAV review stream.

**Why this priority**: Playback and distribution have different goals than
transcription. They should optimize for listening comfort, compatibility, byte
size, and timestamp seeking while preserving the authoritative WAV pair for
MediaScribe.

**Independent Test**: Complete an accepted recording, generate the playback
asset under the same meeting and media revision, then play and seek it in web
review and embedded macOS review. Compare payload size and reviewer listening
comfort against the current mixed WAV playback route.

**Acceptance Scenarios**:

1. **Given** an accepted recording has source audio suitable for review,
   **When** playback generation runs, **Then** the product creates one
   playback/distribution asset associated with the same meeting and media
   revision as the WAV pair.
2. **Given** capture-rate audio is available before transcription downsampling,
   **When** the playback asset is encoded, **Then** it uses that higher-fidelity
   source instead of re-encoding from the 16 kHz transcription WAV pair.
3. **Given** only the 16 kHz transcription WAV pair is available, **When** the
   playback asset is generated, **Then** the product still improves size and
   seekability but does not claim a true fidelity upgrade.
4. **Given** playback audio is available, **When** the owner opens web or
   embedded review, **Then** playback uses the compressed review asset through a
   server-owned route and supports timestamp seek.

---

### User Story 3 - Keep Playback Separate From Download And Sharing Policy (Priority: P1)

As a workspace owner, I want in-page playback, file download, and broader
distribution to remain separate policy decisions, so that a review player does
not accidentally create shareable audio.

**Why this priority**: A playback-friendly file is easier to distribute than raw
WAV. The product must preserve access control, deletion state, and export policy
instead of treating the compressed asset as public media.

**Independent Test**: Exercise allowed playback, blocked playback, allowed
download/export, disabled export, revoked access, and deleted-meeting states.
Confirm that each route fails closed or succeeds with the expected policy.

**Acceptance Scenarios**:

1. **Given** audio download/export policy is disabled, **When** review playback
   is available, **Then** in-page playback remains available only through the
   authorized review route and does not expose a downloadable file.
2. **Given** export or distribution is enabled for the workspace and meeting,
   **When** the owner requests the audio file, **Then** the product serves the
   playback/distribution asset with the approved filename, content type, and
   audit trail.
3. **Given** access is revoked, deletion starts, or retention has purged audio,
   **When** playback or download is requested, **Then** the request fails closed
   without exposing storage paths, signed URLs, or playable bytes.

---

### User Story 4 - Preserve Lifecycle, Diagnostics, And Custody Truth (Priority: P1)

As a privacy, admin, or support owner, I need every source, playback,
distribution, temporary, and transcription artifact to be accounted for, so that
the extra format does not create hidden media copies.

**Why this priority**: Additional media artifacts multiply retention, deletion,
audit, and support risk. The feature is not acceptable unless every derivative
is explainable, retryable, and deletable.

**Independent Test**: Exercise success, partial, retry, failed, offline,
deleted, transcript-only, and policy-blocked flows, then inspect user state,
admin state, support evidence, and deletion reports for every audio artifact
class.

**Acceptance Scenarios**:

1. **Given** playback generation fails while transcription succeeds, **When** the
   user opens the meeting, **Then** the product shows a truthful partial state
   and preserves the accepted WAV transcription source.
2. **Given** the desktop app is offline after recording, **When** it later
   reconnects, **Then** custody resumes without duplicate meetings, duplicate
   accepted media revisions, duplicate playback assets, or duplicate
   transcription submissions.
3. **Given** support evidence is generated, **When** diagnostics describe audio
   status, **Then** they contain only metadata-safe reason codes and no raw
   audio, transcript text, credentials, signed URLs, storage object keys, or
   private local paths.

### Edge Cases

- Browser or embedded macOS review cannot play the selected playback format.
- Only the 16 kHz transcription WAV pair is available, so playback can be
  smaller and seekable but not higher-fidelity than the source.
- Microphone and incoming/system tracks have different durations, delayed
  starts, natural silence, or padding.
- One required transcription WAV is missing, corrupted, protected, or too short.
- Capture-rate audio is available for one source but not the other.
- Mixing microphone and incoming/system audio clips or masks one side of the
  meeting.
- A long meeting creates storage pressure while the playback derivative is still
  pending.
- Upload is interrupted after transcription WAVs upload but before the playback
  asset uploads.
- The meeting is deleted, access is revoked, or retention policy changes while
  playback generation is pending.
- Transcript-only policy is enabled and retained playback audio is not allowed.
- The playback asset is ready while transcript processing is still pending.
- Transcription is ready while playback generation has failed or is still
  pending.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST preserve the current two-file WAV transcription
  source for accepted recordings: microphone audio as `mic.wav` and
  incoming/system audio as `incoming.wav`.
- **FR-002**: The product MUST keep the WAV pair as the normal server-owned
  transcription source; the playback/distribution asset MUST NOT be submitted as
  the normal MediaScribe dual-track input.
- **FR-003**: The transcription WAV pair MUST preserve separate microphone and
  incoming/system roles, continuous timeline truth, silence, padding, duration,
  and alignment needed for transcript and diarization timestamps.
- **FR-004**: The product MUST keep one logical meeting and one accepted media
  revision identity for a recording even when it has multiple audio artifacts.
- **FR-005**: The playback/distribution asset MUST be created only from accepted
  source audio and MUST NOT overwrite, delete, or mutate the transcription WAV
  pair.
- **FR-006**: When capture-rate audio is available before transcription
  downsampling, the playback/distribution asset MUST use that higher-fidelity
  source unless validation proves it unsafe.
- **FR-007**: When only the transcription WAV pair is available, the product MUST
  label the playback asset as size/seek optimized and MUST NOT claim true source
  fidelity improvement.
- **FR-008**: Playback audio MUST be compressed, seekable, and suitable for web
  and macOS embedded review without exposing object-storage URLs, signed URLs,
  local file paths, or direct storage identifiers.
- **FR-009**: Playback audio MUST remain separate from audio download/export
  permission; enabling review playback MUST NOT automatically enable file
  download, public links, or broader distribution.
- **FR-010**: If download/export is allowed, the product MUST serve the optimized
  playback/distribution asset rather than a large mixed WAV, unless policy or
  compatibility requires a truthful fallback.
- **FR-011**: The user MUST NOT need to choose or understand audio formats during
  normal Record, Stop, upload, processing, review, or approved download flows.
- **FR-012**: The product MUST expose user-safe states for each audio artifact:
  pending, generating, available, degraded, failed, blocked, purged, and not
  applicable.
- **FR-013**: A failure to create the playback/distribution asset MUST NOT
  silently delete, overwrite, or terminalize the source recording or WAV
  transcription pair.
- **FR-014**: Every source, transcription, playback, distribution, and temporary
  audio artifact MUST participate in retention, deletion, audit, and local purge
  accounting.
- **FR-015**: Desktop clients MUST NOT call the transcription dependency directly
  and MUST NOT store transcription dependency credentials.
- **FR-016**: Status, diagnostics, logs, analytics, screenshots, and committed
  evidence MUST NOT include raw audio, transcript text, private meeting content,
  credentials, signed URLs, storage object keys, secret paths, or private local
  paths.
- **FR-017**: Access control and deletion state MUST remain authoritative for all
  audio artifacts; unauthorized or deleted meetings MUST fail closed without
  exposing playable audio.
- **FR-018**: Offline and delayed-upload behavior MUST remain safe: local custody
  tracks all required artifacts and resumes without duplicate meetings,
  duplicate playback assets, or duplicate processing after reconnect.
- **FR-019**: Status and release text MUST explain in plain Russian that this
  feature keeps WAV for transcription and adds an optimized playback/distribution
  file, but does not by itself implement echo cancellation, noise suppression,
  transcript editing, public links, or automatic sharing.

### Key Entities *(include if feature involves data)*

- **Source Recording Package**: The local recording truth for microphone audio,
  incoming/system audio, manifest, consent, permissions, alignment, and custody
  status.
- **Transcription WAV Pair**: The required `mic.wav` and `incoming.wav` audio
  files used by the server-owned transcription path, with role mapping,
  duration, format, alignment, and lifecycle state.
- **Playback/Distribution Audio Asset**: The review-oriented compressed audio
  representation used by web review, embedded desktop review, and allowed
  export/download flows, with duration, size, codec family, bitrate class,
  seekability, compatibility state, and lifecycle state.
- **Audio Derivative State**: The per-artifact lifecycle state for generation,
  validation, upload, retry, availability, failure, retention, purge, and
  deletion reporting.
- **Audio Quality Evidence**: Metadata-only validation showing whether the
  playback/distribution asset meets listening, size, compatibility, and
  timestamp-seek thresholds without weakening transcription truth.
- **Artifact Lifecycle Record**: The retention/deletion/audit accounting entry
  for source, transcription, playback, distribution, and temporary audio
  artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of transcription validation cases, the server-owned
  transcription path submits the accepted `mic.wav` and `incoming.wav` pair and
  never submits the mixed playback/distribution asset as the normal dual-track
  source.
- **SC-002**: For a 30-minute dual-track meeting in the validation set, the
  playback/distribution asset is at least 70% smaller than an equivalent
  uncompressed mixed review WAV while remaining reviewable in web and embedded
  macOS playback.
- **SC-003**: Playback starts and seeks to transcript timestamps within 1 second
  in web and embedded macOS review for available playback assets in validation.
- **SC-004**: In reviewer listening checks, at least 90% of sampled playback
  segments are rated equal or better than the current mixed WAV review stream
  for intelligibility and comfort; any claimed fidelity uplift must be backed by
  capture-rate or other higher-fidelity source evidence.
- **SC-005**: Approved download/export validation serves the optimized
  playback/distribution asset with correct access checks, content type,
  filename, byte range behavior, and audit events.
- **SC-006**: 100% of success, partial, failed, deleted, transcript-only, export
  disabled, and policy-blocked scenarios expose truthful per-artifact states for
  source, transcription WAVs, playback/distribution audio, and temporary
  artifacts.
- **SC-007**: Metadata-safety checks find 0 raw audio payloads, transcript text,
  credentials, signed URLs, storage object keys, secret paths, private local
  paths, or private meeting content in diagnostics, logs, screenshots, and
  committed evidence.
- **SC-008**: Reconnect, retry, and duplicate-finalization validation creates 0
  duplicate meetings, 0 duplicate accepted media revisions, 0 duplicate playback
  assets, and 0 duplicate transcription submissions for the same recording.

## Assumptions

- The current MediaScribe-ready transcription contract is two aligned mono
  16 kHz PCM WAV files: `mic.wav` and `incoming.wav`.
- The playback/distribution format, codec, and bitrate are product compatibility
  decisions captured in research and planning; they may change only with
  explicit validation evidence.
- The initial research recommendation is one broadly compatible compressed
  playback/distribution file per meeting, not an additional transcription input.
- The MVP still records microphone and incoming/system audio as separate
  source-role truth. This feature does not reintroduce virtual-driver recording
  as an MVP requirement.
- Echo cancellation, noise suppression, waveform generation, transcript editing,
  native Swift playback controls, public links, and automatic sharing remain
  outside this slice unless a later spec adds them.
- The server-owned review playback route remains the normal playback egress path
  for web and embedded desktop review.
