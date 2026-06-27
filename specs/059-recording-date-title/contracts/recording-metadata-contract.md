# Recording Metadata Contract

This contract defines the feature-level behavior for date, title, title source,
and safe filename metadata. It is intentionally independent of storage object
keys and raw audio/transcript artifacts.

## Date Mapping

New recordings map local manifest timing into meeting creation:

```json
{
  "local_recording_id": "local-recording-stable-id",
  "local_media_revision_id": "local-recording-stable-id--initial",
  "title": "Weekly Product Sync",
  "started_at": "2026-06-26T11:30:00Z",
  "ended_at": "2026-06-26T12:05:12Z",
  "duration_seconds": 2112
}
```

Rules:

- `started_at` is the recording start instant.
- `ended_at` is the recording stop instant.
- `duration_seconds` remains the manifest/package duration.
- Upload, processing, and server create timestamps are lifecycle metadata, not recording date.
- Display timezone can affect labels, but must not replace the canonical recording instants.

## Title Source Order

The 059 resolver chooses the first accepted source:

1. `user_confirmed`: user-provided rename or accepted title from an explicit existing or future title update path.
2. `app_context`: already-available approved app/platform name plus recording date/time.
3. `generic`: generic date/time fallback.

Feature 059 does not introduce a rename UI/API, app/window observer, or
permission prompt solely to discover an app/platform name. If app/platform
context is unavailable or ambiguous, use `generic`.

Calendar title lookup, event matching, and calendar-derived titles are deferred
to feature 060 and must not be implemented by 059.

Platform/window title collection, filtering, and window-derived titles are not
part of feature 059 and must not be implemented by this slice.

## Provenance Shape

The implementation may store this shape locally in manifest/upload metadata and
may include a metadata-only subset in server audit if the existing API path
supports it.

```json
{
  "display_title": "Chrome - 2026-06-26 14:30",
  "title_status": "generated",
  "selected_source": "app_context",
  "selected_confidence": "medium",
  "generated_at": "2026-06-26T12:05:13Z",
  "safe_file_basename": "2026-06-26_14-30_chrome_ab12cd",
  "suppressed_sources": []
}
```

Rules:

- Do not store rejected raw titles in committed evidence.
- Do not include participant emails, raw URLs, tokens, signed URLs, audio, transcript text, or private meeting content.
- Do not include calendar or window source entries in 059 because those sources are not inspected by this slice.
- Persist the chosen title/provenance before first upload create call so retries use stable metadata.
- If a meeting already exists and a later resolver produces a different title, do not mutate through create retry; use an explicit rename/update path in the later implementation plan if needed.

## Safe Filename Basename

Basename pattern:

```text
YYYY-MM-DD_HH-MM_<sanitized-title-slug>_<stable-suffix>
```

Rules:

- The basename is for user-facing export/download/local labels.
- It is not a local package directory name requirement.
- It is not an object storage key.
- It does not rename `manifest.json`, `mic.wav`, or `incoming.wav`.
- It must be stable across retries for the same persisted metadata.

## UI Contract

List row:

- title: visible meeting title;
- date: recording start date label;
- status: existing processing/upload/review state;
- no raw source/provenance shown by default.

Detail page:

- title: visible meeting title;
- recording date/time: start/end or start + duration;
- legacy fallback if start time is missing;
- optional future title source chip only if copy is privacy-reviewed.

Search/sort:

- title search keeps using visible title and existing fallback identity.
- started-date sort uses recording start when present and keeps legacy rows visible.
