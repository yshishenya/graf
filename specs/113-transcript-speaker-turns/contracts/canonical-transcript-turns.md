# Canonical Transcript Turns Contract

## Boundary

- The server owns provider adaptation and returns the review contract.
- Clients never call MediaScribe or another transcription provider to build
  turns.
- The contract contains no provider job id, credential, signed URL, raw audio,
  or diagnostic transcript copy.

## Response shape

`MeetingReviewResponse.transcript` keeps the existing fields and adds:

```json
{
  "available": true,
  "language": "ru",
  "degraded_reason": null,
  "search_enabled": true,
  "segments": [
    {
      "segment_id": "raw-source-id",
      "sequence": 12,
      "start_seconds": 39.120,
      "end_seconds": 40.000,
      "timestamp_label": "00:39",
      "speaker_label": "SPEAKER_01",
      "source_role": "incoming_system",
      "text": "raw source text",
      "confidence_label": "unknown",
      "seekable": true,
      "seek_seconds": 39.120
    }
  ],
  "speaker_turns": [
    {
      "turn_id": "raw-source-id",
      "sequence": 12,
      "start_seconds": 39.120,
      "end_seconds": 41.480,
      "timestamp_label": "00:39",
      "speaker_label": "SPEAKER_01",
      "source_role": "incoming_system",
      "text": "ordered readable text",
      "source_segment_ids": ["raw-source-id", "raw-source-id-2"],
      "seekable": true,
      "seek_seconds": 39.120
    }
  ]
}
```

The example values are illustrative only; no real meeting content belongs in
fixtures or evidence.

## Derivation rules

1. Sort source rows by existing sequence and start time.
2. Keep rows with the same selected processing result and source role in the
   same candidate stream.
3. Merge the next row only when the canonical speaker label is confirmed,
   matches the current turn, and `next.start_seconds - current.end_seconds` is
   between `0` and `1.000` seconds inclusive.
4. Use the first start and last end for the turn; join non-empty text with one
   space; retain all source ids in order.
5. Start a new turn at every other boundary. Never reorder, delete, or rewrite
   raw `segments`.

## Compatibility

- `segments` remains the raw-compatible field and is not removed or renamed.
- `speaker_turns` defaults to an empty list when no final diarization-backed
  source is available.
- Existing clients that ignore unknown fields continue to consume `segments`.
- The server-rendered review uses `speaker_turns` when non-empty and falls back
  to `segments` for transcript-only or incomplete results.

## Validation obligations

- Contract tests cover the field shape and the raw/derived relationship.
- View-model tests cover same-speaker merge, threshold, speaker/track/result
  boundaries, unknown mapping, idempotence, and playback seek timing.
- Rendering tests cover that user-facing transcript rows prefer derived turns
  without exposing provider details.
