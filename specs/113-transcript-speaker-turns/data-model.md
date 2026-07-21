# Data Model: Canonical Speaker Turns

This slice adds no database tables or migrations. The model below describes the
existing source rows and the server-derived review representation.

## Raw Transcript Segment

Existing GRAF-owned source row used to rebuild the readable representation.

| Field | Meaning | Rule |
|---|---|---|
| `segment_id` | Stable source row identity | Must remain available to clients that use raw segments. |
| `sequence` | Provider/import order | Source ordering tie-breaker. |
| `start_seconds`, `end_seconds` | Source timing | Must remain unchanged; invalid intervals do not become merge evidence. |
| `text` | Provider-imported text | Raw content is preserved; it is never rewritten in storage. |
| `speaker_label` | Canonical label when matched to diarization | A display fallback is not sufficient evidence for merging. |
| `source_role` | Canonical source track | Different roles cannot be merged. |
| `processing_result_id` | Bounded imported result/run | Rows from different results cannot be merged. |
| provider provenance | Source adapter metadata | Kept outside the turn semantics and not required by clients. |

## Speaker Turn

Derived read model built from one ordered set of raw segments.

| Field | Meaning | Rule |
|---|---|---|
| `turn_id` | Stable identity for this derived view | Derived from the first source segment identity and result context; rebuilding the same input yields the same value. |
| `sequence` | Review order | Increases with the first source segment. |
| `start_seconds` | First source start | Equal to the first segment in the turn. |
| `end_seconds` | Last source end | Equal to the last segment in the turn. |
| `timestamp_label` | Existing user-facing start label | Uses the existing timestamp formatter. |
| `speaker_label` | Canonical speaker display label | Same label for every merged source segment. |
| `source_role` | Canonical source track | Same role for every merged source segment. |
| `text` | Ordered readable text | Non-empty source texts joined with one space; raw text remains unchanged. |
| `source_segment_ids` | Raw rows represented by the turn | Ordered and complete for the merged sequence. |
| `seekable`, `seek_seconds` | Playback affordance | Seek starts at `start_seconds` and follows existing playback policy. |

## Relationships and boundaries

- One `ProcessingResult` owns many raw transcript and diarization segments.
- One `SpeakerTurn` references one or more raw transcript/review source rows.
- A turn is valid only within one selected processing result and one source
  role.
- Adjacent rows merge only when their canonical labels match and the pairwise
  gap is `0 <= gap <= 1.000` seconds.
- A speaker change, result/run change, source-role change, unknown mapping,
  invalid timing, or gap above one second starts a new boundary.
- Raw rows are the source of truth; turns can be rebuilt after deployment or
  for a legacy result without contacting the transcription provider.

## Lifecycle

1. Provider result import stores raw transcript/diarization rows as it does
   today.
2. Review assembly maps transcript rows to canonical speaker labels.
3. The server derives `speaker_turns` for the response.
4. The review renderer reads turns and retains raw rows in the response for
   compatibility and precise playback.
5. Meeting deletion removes the existing raw rows; no separately retained turn
   artifact remains.
