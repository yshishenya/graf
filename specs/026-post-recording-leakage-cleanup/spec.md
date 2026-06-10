# Feature Specification: Post-Recording Leakage Cleanup

**Feature Branch**: `026-post-recording-leakage-cleanup`  
**Created**: 2026-06-10  
**Status**: Draft  
**Input**: User request: "зафиксируем то как отдельную фичу" after validating that speaker-to-mic leakage can be detected and can block unsafe transcription.

## User Scenarios & Testing

### User Story 1 - Recover a usable local speaker track when cleanup can prove it is clean (Priority: P1)

As a 2brain Rec owner, I want recordings that contain speaker bleed in the local microphone track to be cleaned after recording stops, so that the product can recover a transcription-ready local-speaker track only when it can prove the result is safe.

**Why this priority**: Leakage detection protects transcription truth, but blocked recordings are still a product failure unless the app can safely recover clean local speech.

**Independent Test**: Use a completed recording package where the local microphone track contains measurable speaker bleed and the incoming/system track is available as reference. Run cleanup after recording finalization. The package becomes transcription-eligible only if the cleaned derived local track passes residual leakage and local-speech preservation gates.

**Acceptance Scenarios**:

1. **Given** a finalized package blocked for speaker-to-mic leakage, **When** cleanup produces a derived local track that passes residual leakage and local-speech preservation gates, **Then** the package records the derived track as eligible for later transcription and keeps the original tracks unchanged.
2. **Given** a finalized package blocked for speaker-to-mic leakage, **When** cleanup cannot prove the derived track is clean enough, **Then** the package remains blocked for transcription and the failure reason explains why cleanup was not trusted.
3. **Given** local and remote participants speak at the same time, **When** cleanup is attempted, **Then** local speech must not be removed or materially distorted just to reduce remote bleed.

---

### User Story 2 - Preserve evidence, lineage, and deletion truth (Priority: P1)

As a privacy-conscious owner, I want cleanup to create only clearly labeled derived artifacts with full lineage, so that the original evidence remains auditable and deletion promises remain truthful.

**Why this priority**: Cleanup must not rewrite history. The product needs to know exactly which files are originals, which are derived, and what must be deleted.

**Independent Test**: Create a package where cleanup succeeds. Inspect the package record and deletion inventory. The original microphone and incoming tracks remain intact, the derived track records its source lineage, and deletion coverage includes the derived artifact before it can be used.

**Acceptance Scenarios**:

1. **Given** cleanup succeeds, **When** the package manifest is inspected, **Then** original `mic` and `incoming` evidence remain unchanged and the cleaned local track is marked as a derived artifact.
2. **Given** a derived cleaned track exists, **When** deletion inventory is built, **Then** the derived track is included in deletion truth alongside original recordings, manifests, diagnostics, and any future processing records under 2brain Rec control.
3. **Given** lifecycle registration fails for a derived cleaned track, **When** transcription eligibility is evaluated, **Then** the package remains blocked until the derived artifact is registered or removed.

---

### User Story 3 - Diagnose cleanup outcomes without leaking content (Priority: P2)

As an operator, I want metadata-only cleanup diagnostics, so that I can understand whether cleanup worked without exposing raw audio, transcript text, credentials, signed URLs, or live filesystem paths.

**Why this priority**: This feature touches sensitive local recordings. Diagnostics must help debug quality while preserving the privacy boundary.

**Independent Test**: Run cleanup success and failure scenarios, then export diagnostics. The diagnostic summary contains bounded metrics, outcome status, and reason codes only; it does not contain raw audio content, transcripts, secrets, signed URLs, or live local paths.

**Acceptance Scenarios**:

1. **Given** cleanup succeeds, **When** diagnostics are exported, **Then** diagnostics include metadata-only cleanup status, residual leakage summary, preservation summary, and derived-artifact state.
2. **Given** cleanup fails, **When** diagnostics are exported, **Then** diagnostics include a safe failure reason without embedding raw samples, transcript snippets, credentials, signed URLs, or live local paths.

---

### User Story 4 - Keep recording behavior unchanged during capture (Priority: P2)

As a meeting participant, I want recording start, stop, and visible capture controls to stay simple and truthful, so that cleanup does not introduce hidden recording, route prompts, or live capture surprises.

**Why this priority**: The constitution requires visible capture and one-action stop. Cleanup must happen after capture, not by changing the user's live recording contract.

**Independent Test**: Start and stop a recording with cleanup enabled. During capture, manual start/stop, visible capture indicator, and one-action stop behave exactly as before. Cleanup state appears only after finalization.

**Acceptance Scenarios**:

1. **Given** recording is in progress, **When** cleanup is configured, **Then** the app does not show live leakage prompts, does not block manual recording, and does not hide or alter the capture indicator.
2. **Given** recording stops, **When** finalization begins, **Then** cleanup may run only after the original package has been finalized and the user can still see a truthful post-recording state.

### Edge Cases

- Incoming/system reference track is missing, unreadable, silent, clipped, or too short.
- Local microphone track is missing, unreadable, silent, clipped, or contains only remote bleed.
- Local and remote speakers overlap for long sections.
- Tracks have duration mismatch, clock drift, malformed headers, unsupported format, or corrupted samples.
- Cleanup reduces remote bleed but also removes or distorts local speech.
- Cleanup confidence is unavailable, contradictory, or below the acceptance threshold.
- The derived cleaned artifact is created but lifecycle, deletion, or diagnostic registration fails.
- Disk space is insufficient while writing the derived artifact.
- Long recordings must not create unbounded memory, CPU, or UI delays.
- Existing leakage detection says the package is still unsafe after cleanup.
- Cleanup succeeds technically but diagnostics redaction fails.

## Requirements

### Functional Requirements

- **FR-001**: The product MUST support a post-recording cleanup workflow for finalized local recording packages whose local microphone track contains or may contain speaker-to-mic leakage.
- **FR-002**: Cleanup MUST run only after original recording finalization; it MUST NOT modify realtime capture routing, manual start/stop, visible capture indication, or one-action stop.
- **FR-003**: Cleanup MUST preserve original microphone and incoming/system recording artifacts unchanged.
- **FR-004**: Cleanup MUST create a separate derived local-speaker artifact when it produces a candidate cleaned track.
- **FR-005**: The derived artifact MUST record lineage to the original package, source tracks, cleanup decision, cleanup outcome, and validation evidence.
- **FR-006**: A derived artifact MUST NOT become transcription-eligible unless residual leakage, local-speech preservation, alignment, and lifecycle/deletion registration gates all pass.
- **FR-007**: If cleanup cannot prove the derived track is safe, the package MUST remain blocked or degraded for transcription rather than silently using an unsafe track.
- **FR-008**: Cleanup MUST preserve local speaker speech during double-talk and MUST fail closed when preservation cannot be measured confidently.
- **FR-009**: Cleanup MUST produce metadata-only diagnostics with bounded metrics, reason codes, and artifact state.
- **FR-010**: Cleanup diagnostics MUST NOT include raw audio, transcript text, secrets, credentials, signed URLs, or live local filesystem paths.
- **FR-011**: Cleanup MUST NOT cause the desktop app to send audio directly to MediaScribe or store MediaScribe credentials.
- **FR-012**: Cleanup MUST keep all generated audio local until a future server-side transcription pipeline explicitly accepts the derived artifact under a separate feature.
- **FR-013**: Deletion truth MUST include derived cleaned artifacts before they can be used as eligible recording artifacts.
- **FR-014**: Cleanup MUST surface clear post-recording package states: not attempted, ineligible, succeeded, failed, and blocked pending lifecycle registration.
- **FR-015**: Cleanup MUST include safe failure reasons for missing reference, invalid input, excessive drift, insufficient preservation confidence, residual leakage failure, lifecycle failure, and diagnostic-redaction failure.
- **FR-016**: Cleanup MUST define measurable acceptance thresholds for residual leakage, speech preservation, alignment, and confidence during planning before implementation begins.
- **FR-017**: Cleanup MUST define an evaluation matrix that includes clean packages, contaminated packages, silence, clipping, long recordings, double-talk, drift, malformed input, and deletion/diagnostic failure states.
- **FR-018**: Cleanup MUST avoid unbounded processing; planning must define maximum acceptable processing time, memory use, artifact size, and user-visible waiting behavior.
- **FR-019**: If post-recording cleanup cannot meet the safety and preservation gates, the product MUST keep the package blocked and recommend a future architecture change rather than presenting the audio as clean.

### Key Entities

- **Cleanup Candidate Package**: A finalized local recording package that has original microphone and incoming/system evidence and is eligible for cleanup evaluation.
- **Derived Cleaned Track**: A new local-only audio artifact produced by cleanup, never a replacement for the original microphone track.
- **Cleanup Outcome**: The package-level decision describing whether cleanup was not attempted, succeeded, failed, or is blocked by missing lifecycle registration.
- **Residual Leakage Evidence**: Metadata-only measurements showing whether remote speaker bleed remains in the derived local track.
- **Speech Preservation Evidence**: Metadata-only measurements showing whether local speech remains usable, especially during double-talk.
- **Lifecycle Registration**: The deletion, retention, diagnostic, and manifest bookkeeping required before a derived artifact may be treated as usable.
- **Cleanup Diagnostic Summary**: A redacted, metadata-only summary that helps debug cleanup quality and failure reasons.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For controlled contaminated recording packages with a valid incoming/system reference, cleanup marks a derived track transcription-eligible only when residual leakage and speech-preservation gates pass.
- **SC-002**: For contaminated packages where cleanup cannot prove safety, 100% of packages remain blocked or degraded for transcription with a safe failure reason.
- **SC-003**: In all cleanup success cases, original microphone and incoming/system artifacts remain byte-for-byte unchanged.
- **SC-004**: In all cleanup success cases, derived cleaned artifacts are represented in manifest, lifecycle, diagnostics, and deletion inventory before eligibility is granted.
- **SC-005**: Diagnostic bundles produced after cleanup contain cleanup metadata and reason codes, and contain no raw audio, transcript text, secrets, signed URLs, credentials, or live local paths.
- **SC-006**: Manual start, stop, visible capture indicator, and one-action stop behavior remain unchanged during recording.
- **SC-007**: Existing leakage detection and package finalization validations remain passing after cleanup is introduced.
- **SC-008**: Long-recording cleanup completes within the resource bounds defined in the plan without blocking realtime capture.

## Scope Boundaries

### In Scope

- Post-recording cleanup eligibility and outcome model.
- Derived cleaned local track artifact and lineage.
- Residual leakage and local-speech preservation gates.
- Metadata-only diagnostics and safe failure reasons.
- Deletion and retention accounting for derived artifacts.
- Validation scenarios proving that unsafe cleanup fails closed.

### Out of Scope

- Live echo cancellation during capture.
- Changing the macOS virtual audio driver routing model.
- Automatic meeting start, hidden recording, or no-driver fallback.
- Desktop-to-MediaScribe direct upload.
- MediaScribe credential storage on desktop.
- Server-side transcription ingestion of the derived artifact.
- UI redesign beyond truthful post-recording cleanup status.
- Promising universal deletion outside 2brain Rec control.

## Assumptions

- Existing leakage finalization remains the authority for determining whether a package is unsafe before cleanup.
- Cleanup is initially local and post-recording only.
- The incoming/system track is the preferred reference for removing or suppressing remote speaker bleed.
- Future transcription is handled by a separate server-side feature that can explicitly choose whether to consume a derived cleaned artifact.
- If cleanup quality cannot be proven with metadata-only evidence, the safe product behavior is to keep transcription blocked.
