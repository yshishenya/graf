# Data Model: MediaScribe Result Contract

## MediaScribePollResponse

- `external_job_id`: external job reference passed through from the polling call.
- `status`: MediaScribe job status.
- `reason_code`: backward-compatible safe reason code, sourced from `error_code` when present.
- `error_code`: safe MediaScribe job error code such as `invalid_audio_payload`.
- `error_origin`: safe origin value such as `input_audio` or `mediascribe`.

## MediaScribeResult

- `external_job_id`: external job reference.
- `language`: optional transcript language.
- `transcript_status`: `available` or `unavailable`.
- `transcript_reason`: nullable reason such as `no_recognizable_speech`.
- `transcript`: transcript segments used only when `transcript_status=="available"`.
- `diarization`: diarization segments.
- `summary_status`: existing summary availability state.
- `result_version`: imported result version.

## ProcessingResult

Existing fields remain. New nullable fields:

- `failure_reason`: terminal business reason such as `no_recognizable_speech` or `invalid_audio_payload`.
- `failure_source`: source class such as `input_audio` or `mediascribe`.

Rules:

- `transcript_status=="available"` requires `segment_count > 0` for user download/review availability.
- `transcript_status=="unavailable"` requires `segment_count == 0`.
- Input-audio terminal outcomes set `failure_source=="input_audio"`.

## MeetingOutcomeSet

Existing fields remain. New nullable field:

- `failure_source`: source class for blocked outcome sets, copied from the processing result when transcript absence blocks outcomes.

Rules:

- No-speech and invalid-audio outcomes set `status=="blocked"`.
- Their `failure_reason` is copied from `ProcessingResult.failure_reason`.
- Their `failure_source` is copied from `ProcessingResult.failure_source`.

## MeetingOutcomeGenerationAttempt

Existing fields remain. New nullable field:

- `failure_source`: source class for blocked or failed generation attempts.

Rules:

- Blocked input-audio attempts include `failure_source=="input_audio"` and metadata with safe segment count/status fields.

## ProcessingAuditEvent

No schema change. The allowlist expands to retain these safe metadata keys:

- `mediascribe_job_id`
- `transcript_status`
- `transcript_reason`
- `error_code`
- `error_origin`
- `failure_reason`
- `failure_source`
- `diagnostic_class`

Allowed `diagnostic_class` values for this slice:

- `processed_no_transcript`
- `input_audio_problem`
- `mediascribe_service_problem`
