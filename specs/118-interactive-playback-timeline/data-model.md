# Data Model: Interactive Playback Timeline

## Existing canonical speaker

Derived from the current accepted diarization result and not persisted by this slice.

| Field | Meaning | Rule |
|---|---|---|
| `speaker_key` | Stable meeting-review key such as `speaker_00` | Does not change when the display name changes. |
| `automatic_label` | Canonical fallback label | Remains recoverable after a name is cleared. |
| `source_roles` | Existing source-track roles | Never changed by renaming. |
| `segments` | Accepted start/end intervals | Drive lane drawing and active state on the canonical audio timeline. |
| `transcript_turns` | Canonical turn rows | Carry the same speaker key for transcript following. |

## MeetingSpeakerName

One optional, GRAF-owned display override per canonical speaker in one meeting.

| Field | Type | Rule |
|---|---|---|
| `id` | UUID | Server generated. |
| `workspace_id` | UUID | Required tenant key; request RLS and maintenance only. |
| `meeting_id` | UUID | Required meeting boundary. |
| `speaker_key` | string, max 120 | Normalized existing canonical key; unique with workspace and meeting. |
| `display_name` | string, max 80 | Trimmed visible name; no controls or markup. |
| `updated_by_user_id` | UUID | Actor for the latest accepted value. |
| `created_at`, `updated_at` | timestamp | Server timestamps. |

### Relationships and constraints

- Unique `(workspace_id, meeting_id, speaker_key)`.
- The referenced speaker key must exist in the current authorized meeting review before a write is accepted.
- The row changes presentation only; imported transcript, diarization, timing, and source roles remain immutable.
- An empty submitted name deletes the override row and restores the automatic label.
- Meeting deletion explicitly purges these rows with diarization-derived content; database foreign keys are defense in depth, not the only lifecycle mechanism.

## Playback review projection

| Field | Meaning | Rule |
|---|---|---|
| `duration_seconds` | Playable boundary | Every seek and interval is clamped to it. |
| `current_seconds` | Native audio position | Single runtime source for time labels, progress, playheads, lane activity, and current turn. |
| `speaker_key` | Stable link | Shared by lane and transcript DOM nodes. |
| `start_seconds`, `end_seconds` | Speaker/turn interval | Active when `start <= current < end`; overlapping intervals can all be active. |

## Speaker-name audit event

Uses the existing processing audit model.

| Field | Rule |
|---|---|
| `event_type` | `speaker_display_name_set` or `speaker_display_name_cleared`. |
| workspace/meeting/actor | Required and inherited from the authorized request. |
| metadata | Contains only canonical `speaker_key` and action category. No display name, transcript text, or audio data. |

## State transitions

```text
automatic label -> set override -> replace override -> clear override -> automatic label
```

A rejected or failed write leaves the last confirmed state unchanged.
