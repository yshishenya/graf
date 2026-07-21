# Feature Specification: MediaScribe Result Contract

**Feature Branch**: `091-mediascribe-result-contract`
**Created**: 2026-07-07
**Status**: Implemented and released; complete post-deploy transcript-plus-summary receipt remains open
**Input**: User description: "Update GRAF MediaScribe integration to use the new result contract: `transcript_status`, `transcript_reason`, `error_code`, and `error_origin` must distinguish usable transcripts, processed audio with no recognizable speech, input-audio problems, and MediaScribe service failures."

## User Scenarios & Testing

### User Story 1 - Import Available Transcript (Priority: P1)

When MediaScribe reports a ready job and `result.transcript_status == "available"`, GRAF imports the transcript as the source of truth and can generate meeting outcomes.

**Why this priority**: This preserves the normal happy path and makes the new contract authoritative without regressing transcript review.

**Independent Test**: A mocked ready MediaScribe result with `transcript_status="available"` imports transcript segments, marks `processing_results.transcript_status="available"`, and stores available outcome rows.

**Acceptance Scenarios**:

1. **Given** a MediaScribe job is `ready`, **When** its result says `transcript_status="available"`, **Then** GRAF imports `result.transcript`, counts transcript segments from that array, and leaves summary/outcome generation enabled.
2. **Given** `downloads.transcript` is absent while `transcript_status="available"` and transcript segments exist, **When** GRAF imports the result, **Then** the stored transcript remains the basis for GRAF review and egress is still server-mediated from stored rows.

---

### User Story 2 - Treat No Speech As Processed No Transcript (Priority: P1)

When MediaScribe reports a ready job but `result.transcript_status == "unavailable"` with `transcript_reason="no_recognizable_speech"`, GRAF records a terminal business outcome, not a MediaScribe outage.

**Why this priority**: This directly removes the false impression that MediaScribe broke when the input was processed and no recognizable speech was found.

**Independent Test**: A mocked ready MediaScribe result with no recognizable speech creates an unavailable processing result, blocks meeting outcomes with input-audio provenance, does not generate summary content, and shows/logs the no-speech message.

**Acceptance Scenarios**:

1. **Given** a MediaScribe job is `ready`, **When** the result says `transcript_status="unavailable"` and `transcript_reason="no_recognizable_speech"`, **Then** `processing_results.transcript_status` is `unavailable`, `segment_count` is `0`, `failure_reason` is `no_recognizable_speech`, and `failure_source` is `input_audio`.
2. **Given** this no-speech result exists, **When** outcomes are ensured, **Then** `meeting_outcome_sets.status` is `blocked`, `failure_reason` is `no_recognizable_speech`, `failure_source` is `input_audio`, and summary generation is not run.
3. **Given** a user opens the meeting detail, **When** no transcript exists for this processed recording, **Then** UI copy says: `MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена.`

---

### User Story 3 - Classify Failed Jobs By Error Origin (Priority: P1)

When MediaScribe returns a failed job, GRAF reads `job.error_code` and `job.error_origin` to decide whether the problem belongs to the input audio or to the transcription service.

**Why this priority**: Invalid audio payloads must not trigger service outage retry/alert behavior, while real MediaScribe failures must keep existing retry/alert semantics.

**Independent Test**: Mocked failed polls cover `invalid_audio_payload` from `input_audio` and service-origin failures, proving only service-origin failures use the existing MediaScribe failure path.

**Acceptance Scenarios**:

1. **Given** `job.status=="failed"` with `error_code=="invalid_audio_payload"` and `error_origin=="input_audio"`, **When** GRAF handles the poll result, **Then** it records an unavailable processing result with `failure_reason="invalid_audio_payload"` and `failure_source="input_audio"` and shows `Файл записи не является декодируемым аудио или поврежден.`
2. **Given** `job.status=="failed"` with missing `error_origin` or `error_origin=="mediascribe"`, **When** GRAF handles the poll result, **Then** it treats the outcome as `failure_source="mediascribe"` and keeps the current retry/alert behavior for service failures.

---

### User Story 4 - Keep Diagnostics And Downloads Truthful (Priority: P2)

Support and developer diagnostics show enough metadata to distinguish `input_audio problem`, `mediascribe service problem`, and `processed_no_transcript`, while product UI avoids download actions for absent transcript downloads.

**Why this priority**: Operators need precise incident vocabulary without exposing raw audio, raw transcript text, credentials, signed URLs, or external job identifiers in user-facing surfaces.

**Independent Test**: Processing audit rows include safe metadata for job/result classification, and transcript download actions remain hidden or disabled when the stored transcript is unavailable.

**Acceptance Scenarios**:

1. **Given** a MediaScribe terminal result or failed poll is handled, **When** processing audit metadata is persisted, **Then** it includes safe `mediascribe_job_id`, `transcript_status`, `transcript_reason`, `error_code`, `error_origin`, `failure_reason`, and `failure_source` where available.
2. **Given** `result.downloads.transcript` is absent or the stored transcript is unavailable, **When** GRAF builds review/download state, **Then** it does not show a transcript download action and does not call a MediaScribe transcript download endpoint.

### Edge Cases

- A legacy MediaScribe result omits `transcript_status` but includes transcript segments. GRAF may infer `available` for compatibility, while the new field remains authoritative when present.
- A result says `transcript_status="unavailable"` but includes transcript-like rows. GRAF treats the status as authoritative and does not import text rows as a usable transcript.
- A failed job omits `error_origin`. GRAF treats it as a MediaScribe service problem.
- A failed job uses an unknown non-`input_audio` origin. GRAF treats it as a MediaScribe service problem unless a later contract explicitly adds another business-origin value.
- Diagnostic metadata must never include transcript text, raw audio, credentials, signed URLs, object keys, or live external download URLs.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST parse MediaScribe result `transcript_status` and `transcript_reason` from `GET /jobs/{job_id}/result`.
- **FR-002**: When a ready result has `transcript_status="available"`, GRAF MUST import transcript segments from `result.transcript`, set `processing_results.transcript_status="available"`, count segments from `result.transcript`, and allow outcome generation.
- **FR-003**: When a ready result has `transcript_status="unavailable"` and `transcript_reason="no_recognizable_speech"`, GRAF MUST persist a terminal processed-no-transcript result with `segment_count=0`, `failure_reason="no_recognizable_speech"`, and `failure_source="input_audio"`.
- **FR-004**: GRAF MUST block meeting outcomes for processed-no-transcript results with `meeting_outcome_sets.status="blocked"`, `failure_reason` copied from the processing result, `failure_source="input_audio"`, and no summary generation attempt.
- **FR-005**: GRAF MUST parse MediaScribe poll failed-job `error_code` and `error_origin`.
- **FR-006**: GRAF MUST classify `error_code=="invalid_audio_payload"` and `error_origin=="input_audio"` as an input-audio terminal business outcome, not a MediaScribe service failure.
- **FR-007**: GRAF MUST classify missing `error_origin` or `error_origin=="mediascribe"` as a MediaScribe service problem and preserve existing retry/alert behavior for infrastructure failures.
- **FR-008**: GRAF MUST NOT use the presence or absence of `downloads.transcript` as the main transcript-availability indicator.
- **FR-009**: GRAF MUST NOT show a transcript download action or call a MediaScribe transcript download endpoint when stored transcript content is unavailable.
- **FR-010**: Processing diagnostics MUST persist safe metadata for `mediascribe_job_id`, `transcript_status`, `transcript_reason`, `error_code`, `error_origin`, `failure_reason`, and `failure_source` where available.
- **FR-011**: Developer-facing event names or log/audit messages MUST distinguish `input_audio problem`, `mediascribe service problem`, and `processed_no_transcript`.
- **FR-012**: User-facing copy for no recognizable speech MUST say: `MediaScribe обработал запись, но транскрипт не создан: распознаваемая речь не найдена.`
- **FR-013**: User-facing copy for invalid audio payload MUST say: `Файл записи не является декодируемым аудио или поврежден.`

### Key Entities

- **MediaScribe Job**: External processing job state returned by MediaScribe, including status, safe error code, and error origin.
- **MediaScribe Result**: Result payload for a ready job, including transcript status, transcript reason, transcript segments, diarization segments, summary status, and optional downloads metadata.
- **Processing Result**: GRAF-owned imported outcome from MediaScribe, including transcript availability, segment counts, failure reason, and failure source.
- **Meeting Outcome Set**: GRAF-owned generated or blocked notes/action output state, including blocked failure reason and source when no transcript can support outcomes.
- **Processing Audit Event**: Metadata-only diagnostic record for operators and developers.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Focused tests prove ready/available results import transcript segments and keep outcome generation enabled.
- **SC-002**: Focused tests prove ready/unavailable no-speech results end as processed-no-transcript business outcomes, not MediaScribe service failures.
- **SC-003**: Focused tests prove failed invalid-audio jobs persist input-audio failure metadata and do not use the service-failure retry path.
- **SC-004**: Focused tests prove missing or `mediascribe` error origin keeps existing service-failure handling.
- **SC-005**: UI/view-model tests prove transcript download actions are absent for unavailable transcripts and no-speech/invalid-audio copy is shown without leaking dependency job identifiers.
- **SC-006**: Diagnostic metadata tests prove required safe fields are retained and content-bearing fields remain redacted or excluded.

## Assumptions

- MediaScribe continues to expose job polling at `GET /jobs/{job_id}` and result retrieval at `GET /jobs/{job_id}/result`.
- Existing GRAF server-side storage remains the source for user transcript download; GRAF does not proxy MediaScribe `/downloads/transcript`.
- Existing retry behavior for MediaScribe client HTTP/network failures remains valid unless the failure is explicitly classified as an input-audio business outcome.
- No production deploy is part of this slice.
