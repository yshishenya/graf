# Feature Specification: Transcription Results Pipeline

**Feature Branch**: `045-transcription-results-pipeline`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "Finish the product pipeline for transcription and result delivery in the app. After a local recording is accepted and uploaded, the product should send it through server-owned transcription and diarization, then show processing status and final transcript results in web and desktop review. Do not block upload or transcription because a local audio quality, echo, leakage, silence, or transcription-readiness gate thinks the recording is imperfect. Keep server-side package integrity checks for required files, role mapping, size, and checksums."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload Imperfect Recordings For Transcription (Priority: P1)

As a macOS meeting owner, I want an uploaded recording to continue to transcription even when local quality analysis says the microphone may contain echo, leakage, silence, or degraded readiness, so that I can still get the best available transcript instead of losing the meeting value.

**Why this priority**: The product goal is to produce the best possible transcript and diarization from real meetings. A pre-transcription quality gate can block usable recordings and hide the only available meeting record.

**Independent Test**: Create a structurally valid dual-track recording package whose local quality or leakage state is degraded or failed, upload it, and confirm the package is accepted for server processing unless files, consent, permissions, or integrity are invalid.

**Acceptance Scenarios**:

1. **Given** a recording has required microphone, incoming/system audio, and manifest files with valid package integrity, **When** local leakage or quality readiness is degraded or failed, **Then** upload and transcription eligibility are not blocked solely by that local quality state.
2. **Given** a recording is missing required audio files, has a checksum or size mismatch, lacks accepted recording consent, or violates permissions, **When** upload or finalization runs, **Then** the product blocks the package with a visible safe reason before any transcription job can use it.
3. **Given** a package is accepted for processing despite degraded quality, **When** the user later reviews the meeting, **Then** the result remains labeled truthfully so the user can distinguish "processed from imperfect source" from "not processed."

---

### User Story 2 - Start Processing Automatically After Accepted Upload (Priority: P1)

As a meeting owner, I want accepted uploads to start transcription and diarization without an operator manually triggering a backend endpoint, so that the transcript appears as part of the normal product flow.

**Why this priority**: Upload alone does not complete the user value. The product loop is only complete when an accepted recording moves into processing automatically and exposes truthful status.

**Independent Test**: Upload and finalize a valid meeting package, then observe that exactly one processing attempt is created or reused for the accepted media revision without manual operator steps.

**Acceptance Scenarios**:

1. **Given** a recording package is accepted by the server, **When** processing dependencies are available, **Then** the meeting enters a processing state automatically and exposes that state to the user.
2. **Given** processing dependencies are unavailable, **When** the recording is accepted, **Then** upload remains successful while transcription status shows a retryable or blocked dependency state with a user-safe next action.
3. **Given** the same package is retried, re-finalized idempotently, or picked up more than once, **When** processing starts, **Then** the product reuses the existing processing attempt instead of creating duplicate transcription jobs or duplicate result records.

---

### User Story 3 - See Transcript And Diarization Results In Web And Desktop (Priority: P1)

As a meeting owner, I want the final transcript, speaker/provenance state, and processing result to appear consistently in both the web cabinet and the installed desktop app, so that I can review the meeting wherever I entered the flow.

**Why this priority**: The user experience is broken if transcription finishes on the server but the application still looks empty, stale, or inconsistent.

**Independent Test**: Process one uploaded meeting through the approved server path, then open the same meeting from web review and desktop embedded review and compare visible status, transcript availability, diarization availability, and speaker/provenance labels.

**Acceptance Scenarios**:

1. **Given** transcription and diarization are imported successfully, **When** the owner opens web review, **Then** transcript segments, diarization state, source/provenance labels, and generated result status are visible for the accepted media revision.
2. **Given** the same meeting is opened from the desktop app, **When** the embedded review route loads, **Then** it shows the same ready, partial, failed, or blocked truth as the web cabinet.
3. **Given** transcription is still running or failed, **When** the user opens either review surface, **Then** the UI explains the status without inventing transcript content or hiding successful upload state.

---

### User Story 4 - Preserve Privacy And Content Boundaries (Priority: P1)

As a privacy and security owner, I need the processing loop to keep audio, transcript text, credentials, signed URLs, and private meeting content out of logs, diagnostics, status payloads, and committed evidence, so that the product can be debugged without leaking sensitive meeting data.

**Why this priority**: This feature crosses local recording, server upload, external transcription, stored transcript content, and review UI. It must preserve product trust while making status observable.

**Independent Test**: Run success, degraded, dependency-blocked, and failed processing flows, then inspect status responses, logs, diagnostics, and evidence artifacts for forbidden content.

**Acceptance Scenarios**:

1. **Given** a meeting is processed successfully, **When** diagnostics or evidence are generated, **Then** they contain only metadata-safe proof and never raw audio, transcript text, credentials, signed URLs, or private local paths.
2. **Given** a processing dependency fails, **When** the user or operator checks status, **Then** the product exposes safe reason codes and recovery state without leaking provider responses or meeting content.

### Edge Cases

- A recording has audible speaker leakage or local echo but all required files and integrity checks pass.
- A recording has a local "failed" transcription-readiness state because quality could not be proven, but the package is still structurally valid.
- Required microphone, incoming/system audio, or manifest files are missing.
- Track roles are swapped, duplicated, truncated, or have checksum/size mismatch.
- The user recorded offline and upload resumes later after a restart.
- Processing dependencies are disabled, unhealthy, slow, or temporarily unavailable.
- Processing succeeds but transcript, diarization, or summary content is partial.
- Processing is retried after a worker crash, server restart, network failure, or duplicate pickup.
- The meeting is deleted, access is revoked, or local data is purged while processing is pending.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST allow structurally valid recording packages to proceed to upload and transcription even when local audio quality, leakage, echo, silence, or transcription-readiness analysis is degraded, failed, inconclusive, or unavailable.
- **FR-002**: The product MUST continue to block transcription for packages that lack required recording consent, violate recording permissions, are missing required files, have invalid role mapping, have duplicate required roles, or fail size/checksum integrity.
- **FR-003**: The product MUST clearly separate upload integrity status from audio quality status so users and support can tell whether a meeting is blocked because the package is unsafe or merely processed from an imperfect source.
- **FR-004**: After the server accepts a recording package, the product MUST automatically create or reuse one processing attempt for the accepted media revision when processing is enabled and dependencies are available.
- **FR-005**: Processing pickup MUST be idempotent: retries, duplicate pickup attempts, and repeated status checks MUST NOT create duplicate transcription jobs or duplicate imported transcript/diarization results for the same accepted media revision.
- **FR-006**: The product MUST expose user-safe processing states for not submitted, starting, submitted, polling, importing, ready, partial, retryable failure, blocked dependency, blocked package, and terminal failure.
- **FR-007**: Successful processing MUST make transcript availability, diarization availability, speaker/provenance labels, and accepted media revision identity visible in both web review and desktop embedded review.
- **FR-008**: Failed or blocked processing MUST preserve successful upload state separately from transcription state and MUST provide a safe reason and next action instead of implying that the recording was lost.
- **FR-009**: The product MUST preserve offline and delayed-upload behavior: a local package may be recorded and queued without network, then uploaded and processed later without creating duplicate meetings.
- **FR-010**: Status, diagnostics, logs, analytics, and committed evidence MUST NOT include raw audio, transcript text, private meeting content, credentials, signed URLs, secret paths, or private local paths.
- **FR-011**: Deletion and access-control state MUST remain authoritative during processing; deleted or unauthorized meetings MUST not expose transcript results or silently restart processing.

### Key Entities *(include if feature involves data)*

- **Recording Package**: The local meeting capture bundle containing manifest truth, microphone audio, incoming/system audio, package state, consent/permission truth, and quality or leakage observations.
- **Accepted Media Revision**: The immutable server-accepted representation of a recording package that processing and later review results attach to.
- **Processing Attempt**: The lifecycle record for transcription and diarization work on an accepted media revision, including current state, retry history, dependency state, and safe reason codes.
- **Transcript Result**: The stored reviewable text segments, timing, speaker/provenance state, diarization availability, and import status created from processing.
- **Review Surface**: The web cabinet and desktop embedded view where users see meeting status, transcript readiness, transcript content when authorized, and blocked/failed explanations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of structurally valid test packages with degraded, failed, inconclusive, or unavailable local audio quality readiness proceed to server processing eligibility unless blocked by consent, permission, missing-file, role, size, or checksum integrity failures.
- **SC-002**: 0 duplicate processing jobs and 0 duplicate imported result sets are created across repeated upload finalization, processing pickup, worker restart, and retry scenarios for the same accepted media revision.
- **SC-003**: For a healthy processing environment, an accepted uploaded meeting reaches a visible processing state within 60 seconds without manual operator action.
- **SC-004**: For a one-hour internal benchmark recording where the transcription dependency returns a ready result, product-owned orchestration before submission and after result availability completes in under 3 minutes.
- **SC-005**: Web review and desktop embedded review show matching processing readiness, transcript availability, diarization availability, and safe blocked/failed states for the same processed meeting in all contract tests.
- **SC-006**: Metadata-safe diagnostics and evidence checks find 0 raw audio payloads, transcript text, credentials, signed URLs, secret paths, private local paths, or private meeting content outside controlled product stores.

## Assumptions

- Dual-track microphone plus incoming/system audio remains the primary MVP transcription source.
- Testing two people speaking into the same local microphone is out of scope for this slice.
- Echo cancellation and noise suppression research remains in feature `044`; this feature does not require AEC to be product-ready before transcription can run.
- The server-owned transcription path remains the only approved external transcription route; the desktop app does not send audio directly to transcription providers and does not store provider credentials.
- Transcript editing, local media trimming, replace/reprocess flows, and full video review remain outside this slice unless a later spec adds them.
- Existing authentication, meeting identity, upload queue, review authorization, retention, and deletion policies remain authoritative.
