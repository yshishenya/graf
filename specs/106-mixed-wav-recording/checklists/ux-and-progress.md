# UX and Progress Requirements Checklist: Чистый единый аудиопоток

**Purpose**: Validate user-visible capture control, upload progress, playback and degradation requirements before implementation.

**Created**: 2026-07-17

**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [quickstart.md](../quickstart.md)

## Requirement Completeness

- [X] CHK001 Are manual Start/Stop, persistent active-capture indication and one-action Stop requirements stated for normal, degraded and processing-pending states? [Completeness, Spec §FR-006]
- [X] CHK002 Are user-visible requirements defined for a healthy transcript with unavailable playback, a valid playback with unavailable processing, and an invalid canonical WAV? [Coverage, Spec §User Story 2/§FR-012]
- [X] CHK003 Are upload-progress requirements defined for the whole v5 package rather than a count of completed audio files? [Completeness, Spec §FR-015, Plan §3]
- [X] CHK004 Is a meaningful intermediate progress state required between zero and completion for normal multipart upload, including retries/resume? [Measurability, Spec §FR-015/SC-010, Plan §3]
- [X] CHK005 Are existing historical-recording views required to remain understandable without presenting historical dual packages as a selectable new recording mode? [Consistency, Spec §FR-010, Plan §5]

## Clarity And Consistency

- [X] CHK006 Is “the user hears incoming audio unchanged” quantified consistently with route preservation and the ≤1 dB requirement? [Clarity, Spec §FR-006/SC-005]
- [X] CHK007 Are distinctions among capture integrity failure, upload failure, processing block, playback unavailable and transcript availability clear in product wording? [Clarity, Spec §Edge Cases/FR-012]
- [X] CHK008 Is the prohibition on exposing audio processing mode, AEC settings, levels or rollback controls to the user consistent with the stated result-first product goal? [Consistency, Spec §Assumptions/FR-005/FR-009]
- [X] CHK009 Are expectations for one chronological user transcript stated without promising impossible speaker accuracy in unproven physical acoustic conditions? [Clarity, Spec §User Story 1/SC-003, Research §Finding: dual transcription]

## Accessibility And Recovery Coverage

- [X] CHK010 Are visible capture, Stop and processing/degraded state requirements complete for keyboard and assistive-technology users? [Completeness, Spec §FR-014/SC-011, Constitution §II]
- [X] CHK011 Are requirements defined for a route/device change or permission loss during capture without hiding the active state or the next safe action? [Coverage, Spec §Edge Cases/FR-006]
- [X] CHK012 Are retry, local-purge and retention states described in a way that avoids claiming an upload/transcript/playback result that has not been confirmed? [Consistency, Spec §FR-011/FR-012]
- [X] CHK013 Are product-copy requirements explicit that the playback artifact is for listening only and the canonical WAV is the independent transcription source? [Clarity, Spec §FR-003/FR-004]

## Acceptance Criteria Quality

- [X] CHK014 Can an independent reviewer measure upload-progress smoothness, route change and incoming-level delta from the stated evidence without recording private meeting content? [Measurability, Spec §SC-005/SC-010, Quickstart §Installed-app hardware acceptance]
- [X] CHK015 Are user-visible hardware and full-pipeline acceptance requirements sufficiently separate from internal diagnostics to preserve a clean product surface? [Consistency, Plan §Validation Plan, Product Gates §UX And Brand Distance]

## Review Result

- Requirements review passed on 2026-07-17 after explicit accessibility and byte-weighted progress requirements were added to the specification.
