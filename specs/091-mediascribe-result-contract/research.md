# Research: MediaScribe Result Contract

## Decision 1: `transcript_status` Is The Import Source Of Truth

**Decision**: Parse and persist `result.transcript_status`; use it as the primary transcript availability indicator when importing results.

**Rationale**: MediaScribe now separates technical completion from transcript availability. A ready job with no recognizable speech is successful processing with no transcript, not a malformed result.

**Alternatives considered**:

- Keep using `bool(result.transcript)`: rejected because it cannot distinguish old empty transcript failures from the new terminal business outcome.
- Use `downloads.transcript`: rejected because MediaScribe may omit the download when no transcript exists and returns 409 for empty transcript downloads.

## Decision 2: Persist Failure Reason/Source On GRAF-Owned Rows

**Decision**: Add nullable `failure_reason` and `failure_source` to `processing_results`, add nullable `failure_source` to `meeting_outcome_sets`, and add nullable `failure_source` to generation attempts for evidence symmetry.

**Rationale**: Current rows can store transcript availability and outcome `failure_reason`, but cannot represent whether the failure belongs to input audio or MediaScribe. Encoding source inside a generic reason string would be brittle and would not satisfy diagnostics.

**Alternatives considered**:

- Store everything only in audit metadata: rejected because UI and outcome logic need durable source/reason without searching audit rows.
- Add a new diagnostics table: rejected as larger than needed for two nullable metadata fields on existing lifecycle rows.

## Decision 3: Business Outcomes End Processing Without Service Failure Retry

**Decision**: For ready/unavailable no-speech and failed/input-audio invalid payload, persist an imported processing result with no transcript and set the processing workflow to `processed` with the business reason recorded.

**Rationale**: The MediaScribe interaction is terminal and understood. Marking the workflow `failed_*` would keep the false service-failure signal. The review surface can still show unavailable transcript copy from the processing result failure metadata.

**Alternatives considered**:

- Mark workflow `blocked`: rejected because it suggests operator action on processing infrastructure, while the recording simply has no usable speech or is not decodable audio.
- Leave workflow `failed_terminal`: rejected because it preserves the false MediaScribe-failure interpretation.

## Decision 4: Keep Service Failures On Existing Retry/Alert Path

**Decision**: Missing `error_origin`, `error_origin=="mediascribe"`, and unknown origins remain MediaScribe service problems and use the existing failed terminal/retryable classification path.

**Rationale**: The new contract only creates a business exception for explicit input-audio origin. Existing operational behavior is safer for ambiguous or service-origin failures.

## Decision 5: Diagnostics Use Existing Processing Audit Events

**Decision**: Record `processed_no_transcript`, `input_audio_problem`, and `mediascribe_service_problem` processing audit events with allowlisted safe metadata.

**Rationale**: Processing audit events are already tenant-scoped, metadata-only, and tied to the local MediaScribe job row. This avoids new logging infrastructure and keeps raw content out of diagnostics.

## Decision 6: UI Copy Uses Existing Review Empty-State Path

**Decision**: Map `no_recognizable_speech` and `invalid_audio_payload` to the requested Russian copy in cabinet processing/review view models.

**Rationale**: The existing empty-state renderer already displays `reason_label` before generic fallback copy. This keeps UI scope small and avoids a new error banner system.
