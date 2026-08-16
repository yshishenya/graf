# Data Model: Meaningful Recording Titles

No new entity or database column is required.

## Existing inputs

### Meeting

| Field | Role | Validation / behavior |
|---|---|---|
| `id` | Stable recording identity | Never changes as a result of title projection |
| `title` | Stored source title | Bounded and screened with existing metadata safety rules |
| `title_source` | Source/authority marker | `user_confirmed`, `calendar`, `app_context`, `generic`, upload/file-name sources, or legacy value |
| `started_at` | Recording start instant | Used for the visible date/time suffix |
| `recording_display_timezone_offset_minutes` | Display timezone snapshot | Reused for deterministic local presentation |
| `local_recording_id` | Local artifact correlation | Not used as the primary visible title when metadata exists |

## Derived projection

`display_title` is computed without persistence:

```text
user_confirmed title                                  -> exact safe title
calendar title + recording start date/time            -> formatted automatic title
source application title + recording start date/time  -> formatted automatic title
generic label + recording start date/time             -> localized fallback
```

The projection is consumed by `MeetingListItem`, the cabinet row renderer,
meeting detail rendering, shared-with-me cards, search/sort title paths, and
the embedded desktop cabinet. It must not change meeting IDs, audio artifact
paths, upload state, processing state, or deletion state.

## State behavior

- Automatic titles may change when a calendar match is applied.
- User-confirmed and upload-provided titles remain authoritative.
- Missing/unsafe title input falls through to the next safe source.
- Missing start time yields the existing safe non-empty fallback rather than an
  exception or empty label.
