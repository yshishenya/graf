# Web Meeting Review Complete

## Purpose

Deliver the product value after processing: transcript, playback, summary,
decisions, action items, questions, follow-ups, provenance, and safe actions.

## Layout

- Target: `1440 x 900`.
- Sidebar: `248 px`.
- Header: `64 px`.
- Review body:
  - Transcript column: fluid, minimum `620 px`.
  - Review/inspector panel: `360 px`.
- Playback bar pinned at bottom of review body.

## Header

- Meeting title.
- Date/time.
- Duration.
- Source provenance.
- Status chip: `Ready` or `Notes ready`.
- Actions:
  - `Speakers`.
  - `Copy summary`.
  - `Share` browser-only or handoff from desktop.
  - `Export`.
  - More menu.

More menu:

- Find in transcript.
- Export transcript.
- Download audio when policy allows.
- Save/favorite.
- Delete meeting.
- Open desktop status when applicable.

## Transcript Column

Required:

- Search in transcript.
- Timestamp column.
- Speaker label.
- Segment text.
- Active playback highlight.
- Segment overflow for future edit/copy.

Rules:

- Transcript is never hidden below notes.
- Speaker assignment, naming, and merge are server-owned web behavior. They are
  available in the browser cabinet and in the desktop app through the
  allowlisted embedded route `/desktop/meetings/:id/speakers`; native macOS
  does not own the editing logic.
- Speaker separation uses one horizontal timeline lane per speaker, with only
  that speaker's segments and talk-time percentage on the lane. Do not collapse
  all speakers into one combined multicolor strip.
- Long segments wrap without covering controls.

## Review Panel

Tabs or sections:

- Summary.
- Decisions.
- Action items.
- Questions.
- Follow-ups.
- Source and status.

Each section must show provenance and degraded state if generated from partial
or low-confidence transcript.

## Playback

- Play/pause.
- Timeline.
- Current time and duration.
- Speed.
- Jump by segment.
- Speaker distribution optional.

Audio controls appear only when audio is available and access policy allows it.

## AI Drawer

Allowed as secondary:

- `Ask about this meeting`.
- Scope chip: `This meeting`.

Deferred:

- `All meetings` scope until privacy/retention search is specified.
- Personalization flows.

## Share And Access

Browser owns access edits:

- Invite-only default.
- Workspace/team/public-link changes require explicit confirmation.
- Desktop can open browser share, but should not edit access in-app.

## Acceptance Evidence

Covered by Figma `V8 07 - Транскрипт и спикеры в приложении`,
`V8 08 - Дорожки назначения спикеров`, `V8 11 - Веб-детали встречи и транскрипт`, and
`design/validation-evidence.md`.
