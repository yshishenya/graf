# Data Model: Canonical Provider Speaker Turns

## Raw ASR Segment

Existing `TranscriptSegment`; immutable unattributed evidence.

- `segment_id`, `processing_result_id`, `sequence`
- exact Decimal `start_seconds`, `end_seconds`
- `text`, source role and original role

It is never mutated or decorated with a speaker winner.

## Provider Speaker Turn

Existing `DiarizationSegment`; received attributed evidence.

- `segment_id`, `processing_result_id`, `sequence`
- exact Decimal `start_seconds`, `end_seconds`
- raw `speaker_label` retained as `provider_speaker_key`
- `text`, source role

## Canonical Speaker Turn

Pure GRAF projection, not a new table.

- stable `turn_id`
- `processing_result_id`, source segment IDs, sequence
- exact start/end values
- source text and role
- `provider_speaker_key` (nullable for fallback)
- stable GRAF `speaker_key`
- ordinal `canonical_label`
- resolved `speaker_label`
- attribution state: `confirmed`, `unknown`, `mixed`, or `uncertain`
- result state: `accepted` or `degraded_provider_result`
- overlap flag

Accepted turns map one-to-one to provider rows. Structurally unsafe degraded
turns map one-to-one to valid non-empty ASR evidence and never use unsafe
provider text. When degradation is caused only by a tiny explicit unknown,
contract-valid provider turns remain one-to-one and the unknown row stays one
non-confirmed turn.

## Canonical Speaker Model

- ordered raw ASR evidence
- ordered canonical turns
- provider contract state and bounded reasons
- speaker identity map
- attribution diagnostics

All consumers receive this same model or a lossless projection of it.

## Speaker Identity

- `provider_speaker_key`: exact raw provider label
- `speaker_key`: `provider:<processing-result-id>:<sha256-prefix>`
- `canonical_label`: display-order `SPEAKER_XX`
- `display_name`: optional saved name resolved by stable key
- `confirmed`: false for unknown/mixed/uncertain
- `renameable`: true only for confirmed provider identities

## Provider Contract Diagnostics

Content-free object:

- `state`: `accepted` or `degraded_provider_result`
- `defect_origin`: `provider` or `graf`
- bounded reason codes
- provider job ID and available version identifiers
- raw/accepted turn counts
- multi-label conflict count
- unknown/tiny identity count
- duplicate full-text count
- text conservation status
- source-result hash

## State transitions

```text
received -> normalized -> accepted -> canonical turns
                       |-> degraded unsafe result -> ASR evidence once
                       \-> degraded tiny UNKNOWN -> valid turns + unknown once
```

No transition silently repairs provider attribution. Re-running the same source
result produces byte-equivalent identity keys, ordering, and state.
