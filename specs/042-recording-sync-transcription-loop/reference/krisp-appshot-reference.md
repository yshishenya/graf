# Krisp Appshot Reference: Recording Sync And Transcription Loop

Date: 2026-06-18

## Purpose

This file preserves the useful UX/product observations from user-supplied Krisp
appshots without committing private screenshots, account identifiers, meeting
titles, emails, transcript text, or proprietary visual assets.

Raw appshots, if needed locally, belong only in:

```text
specs/042-recording-sync-transcription-loop/reference/private-appshots/
```

That directory is intentionally ignored by git. Do not move raw reference
screenshots into committed evidence. Use synthetic or redacted screenshots for
PR/release evidence.

## Supplied Appshot Sequence

The user supplied Krisp appshots with these timestamps:

- `2026-06-17T22-11-49.956Z`: meeting list with `New` menu exposing live
  record and file upload.
- `2026-06-17T22-12-25.421Z` and `2026-06-17T22-12-29.238Z`: meeting detail
  on Recording & Transcript with transcript, playback, speaker timeline,
  transcript rating prompt, and native side capture controls visible.
- `2026-06-17T22-14-38.885Z`: Notes view with generated key points and action
  items.
- `2026-06-17T22-15-04.578Z`: Recording & Transcript view with speaker
  assignment/search popover.
- `2026-06-17T22-16-01.181Z`, `2026-06-17T22-16-04.140Z`, and
  `2026-06-17T22-16-17.240Z`: meeting list with upcoming meetings, contains
  filter, sort menu, type/status hints, and compact rows.
- `2026-06-17T22-17-30.856Z`, `2026-06-17T22-18-09.580Z`,
  `2026-06-17T22-18-41.505Z`, and `2026-06-17T22-19-00.520Z`: upload modal
  with language selector, drag/drop or click upload target, supported
  format/size/duration copy, selected file progress, cancel control, and close
  confirmation.

## Safe Observations To Reuse

- Active recording remains persistently visible while the user navigates list,
  upload, notes, and transcript views.
- Meeting list is compact and work-oriented: left navigation, upcoming
  meetings, sortable rows, filters, and a single `New` menu that separates
  live recording from file upload.
- Upload flow is understandable: choose transcription language, drag/drop or
  click file, show supported formats, show size/duration limits, show selected
  file and progress.
- Krisp warns that closing the upload window cancels the current upload and the
  file will be lost. 2brain Rec should intentionally improve this behavior:
  UI dismissal, network loss, or app restart must not discard a local recording
  package or resumable queue state.
- Detail review separates generated notes from Recording & Transcript. The
  transcript view combines timestamped segments, speaker labels, playback,
  speaker timeline/contribution indicators, and transcript quality feedback.
- Speaker assignment/search is useful, but transcript editing and speaker
  editing are not part of feature `042`; they remain future feature work.

## Product Decisions For 042

- Keep native recording state visible outside the embedded review route.
- Use server-owned web/desktop review for transcript display so browser and
  embedded desktop stay consistent.
- Preserve upload truth separately from transcription truth.
- Treat local media persistence and resumable upload state as a core advantage
  over reference-app upload cancellation behavior.
- Commit only sanitized descriptions or synthetic screenshots.

## Forbidden In Committed Evidence

- Raw appshot PNGs from the user-supplied Krisp session.
- Real meeting titles, attendee names, emails, account identifiers, or
  transcript snippets from the appshots.
- Krisp visual assets, proprietary copy beyond short category labels, or brand
  expression.
- Local filesystem paths, tokens, cookies, signed URLs, credentials, or raw
  audio/media names from private sessions.
