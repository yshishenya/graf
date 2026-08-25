# Data Model: MediaScribe v0.5.3 integration fidelity

## WordItem

| Field | Type | Required | Rules |
|---|---|---:|---|
| `word` | string | yes | Non-empty provider word text; retained as provider data. |
| `start` | number or null | no | Optional word start; if present, non-negative and not later than `end`. |
| `end` | number or null | no | Optional word end; if present, positive and not earlier than `start`. |
| `probability` | number or null | no | Optional provider confidence; no user identity semantics. |

`words` on a diarization block is absent, `null`, or a list of `WordItem`. Unknown keys are not relied upon by GRAF and are ignored at the typed boundary unless needed for forward-compatible DTO diagnostics.

## Provider diarization block

Existing provider DTO `MediaScribeDiarizationSegment` gains `words: list[WordItem] | None` and retains:

- start/end seconds;
- provider speaker key;
- complete text;
- optional normalized and original source role;
- sequence assigned only for stable import ordering, not for re-segmentation.

The DTO is not a new user identity. Speaker labels remain job-local and `UNKNOWN` remains uncertainty.

## Durable storage

`diarization_segments` gains nullable `words_json` JSON storage. It is scoped by the existing `workspace_id`, `meeting_id` and `processing_result_id` lineage and is removed by the existing result/deletion lifecycle. The value contains only validated WordItem objects and never provider credentials or signed URLs.

Existing rows remain valid with `words_json = null`.

## Source role normalization

| Provider input | Result mode | Stored normalized role | Original token |
|---|---|---|---|
| `mic` | any valid role-bearing result | `mic` | optional original |
| `incoming` | any valid role-bearing result | `incoming` | optional original |
| `mixed` | single-track or mixed | `mixed` | optional original |
| omitted/null | single-track | `mixed` | null |
| omitted/null | dual-track | `unknown_provider_state` / degraded | null |
| bounded unknown token | any | `unknown_provider_state` | bounded token |

## Result and recovery invariants

- `ProcessingResult` is user-visible only when transcript and matching diarization are available; summary status is independent.
- `source_result_hash` includes the normalized typed result, including words, so a changed provider result cannot be mistaken for the same imported payload.
- A recovery schedule has one active generation per business attempt. Manual check increments/claims the generation through the existing atomic store fence.
- Temporal history receives only the existing bounded workflow payload and safe metadata; words remain in GRAF result storage, not Search Attributes or ordinary operational logs.
