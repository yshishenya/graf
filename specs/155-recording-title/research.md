# Research: Meaningful Recording Titles

## Decision 1: Fix the shared display projection, not capture or persistence

**Decision**: Keep the existing recording metadata contract and change the
server cabinet projection used by list/detail/shared views.

**Rationale**:

- `RecordingMetadataResolver` already produces an app-context title and a
  generic dated title.
- `DesktopUploadClient` already sends `title`, `title_source`, start time, and
  display timezone offset.
- The macOS app embeds the web cabinet, so the same server projection serves
  both requested surfaces.
- `Meeting` already stores title source and display-timezone metadata.

**Alternatives considered**:

- Add a new native macOS recording-list UI: rejected; the existing product
  surface is the embedded cabinet and this would duplicate presentation logic.
- Add a database migration or a second display-title field: rejected; the
  needed inputs already exist and the title is a deterministic projection.
- Rename local audio files: rejected; explicitly out of scope and risks
  breaking artifact identity or upload references.

## Decision 2: Apply source precedence at the presentation boundary

**Decision**: Use existing source authority and format only automatic titles:

1. user-confirmed title — preserve exactly after existing safe path cleanup;
2. calendar title — append the recording start date/time;
3. source application title — restore the app label and append the recording
   start date/time;
4. generic recording label — use the existing localized dated fallback.

Manual-upload and file-name-derived titles retain their existing semantics.

**Rationale**: `title_source` already distinguishes replaceable automatic
metadata from authoritative user/upload values. The current bug is the
`safe_title`/`meeting_list_title` branch that hides non-authoritative generated
titles as «Запись», not missing data.

**Alternatives considered**:

- Mutate stored calendar titles to include formatted time: rejected; storage
  should retain the source title and avoid duplicate formatting on retries.
- Format in each HTML template: rejected; it would make list, detail, shared,
  and embedded surfaces drift.
- Use the local filename as the primary title: rejected; filenames are an
  artifact concern and can be stale, opaque, or unsafe.

## Decision 3: Reuse existing metadata safety and timezone behavior

**Decision**: Continue using `safe_metadata_text`, HTML escaping, the recording
display timezone offset, and the existing Russian short-date presentation.

**Rationale**: The repository already fails closed for URLs, emails, control
characters, and credential-like metadata, and already has a single helper for
recording-time labels.

**Alternatives considered**:

- Introduce a new locale/date library: rejected; existing native/Python date
  formatting covers the requirement.
- Display raw event/app metadata directly: rejected; violates the existing
  metadata safety boundary.

## Repository and external research notes

Repository inspection covered the macOS metadata resolver, upload payload,
meeting persistence, calendar matching, cabinet query/view-model/rendering
paths, and their existing tests. External product/forum/GitHub research was
used as a constraint check: meeting titles are useful for human retrieval,
but window/application labels are only a fallback because they can be missing
or generic; therefore the calendar title must win when available and the
recording timestamp must remain part of the visible identifier.
