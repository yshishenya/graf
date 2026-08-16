# Recording Title Contract

## Scope

This is a presentation contract over the existing meeting and upload
contracts. It adds no endpoint and no database field.

## Inputs

- `title`: optional bounded safe source title.
- `title_source`: source authority marker.
- `started_at`: optional recording start timestamp.
- `recording_display_timezone_offset_minutes`: optional display offset.

## Output

Every recording list/detail projection returns a non-empty safe display title.
Automatic output follows this precedence:

1. calendar title plus recording date/time;
2. source application title plus recording date/time;
3. localized generic recording label plus recording date/time.

An explicitly user-confirmed title remains unchanged. Existing manual-upload
and file-name-derived title behavior remains unchanged.

## Safety and compatibility

- Apply existing metadata safety validation before projection.
- HTML consumers escape the projected title.
- Date/time uses the recording's stored display offset.
- Projection must be deterministic and must not mutate persisted title data.
- Existing meeting identity, media paths, processing, playback, sharing, and
  deletion contracts remain unchanged.
