# Phase 0 Research: Interactive Playback Timeline

## Decision 1: Use one inset time scale for every track

- **Decision**: Keep the native range input for accessibility and align each speaker lane to the same inner scale bounded by the range thumb radius. Share label, scale, and trailing columns across the progress row and every lane.
- **Rationale**: The current mismatch is structural: playback uses 54/track/54 columns while speaker lanes use 86/track/42 columns, and native range endpoints are inset by half a thumb. One CSS scale fixes the root cause for every lane without replacing keyboard-ready native behavior.
- **Alternatives considered**:
  - Add a constant time offset: rejected because the error is horizontal layout, not audio timing.
  - Replace the range with a custom slider: rejected because it recreates keyboard, focus, and accessibility behavior already supplied by the platform.

## Decision 2: Route all seeks through one client function

- **Decision**: Main range input, speaker-lane pointer input, skip buttons, and transcript timestamps call one bounded seek/sync function. Speaker clicks compute time from the shared inner scale; ordinary playback updates visible time, playheads, and active lanes through the same synchronization path.
- **Rationale**: A single path prevents sibling controls from drifting and gives transcript following one deterministic trigger boundary.
- **Alternatives considered**:
  - Separate listeners with duplicated math: rejected because the current bug is inconsistent surfaces.
  - Poll playback time independently from each lane: rejected as more code and more state.

## Decision 3: Follow transcript only after deliberate seeks

- **Decision**: A deliberate seek centers the nearest canonical turn at or before the target (the first turn before any speech). Ordinary playback updates the current-turn visual state but does not continuously scroll or move focus.
- **Rationale**: This meets the requested jump-to-text behavior without fighting a reviewer who is reading elsewhere.
- **Alternatives considered**:
  - Auto-scroll on every time update: rejected because it steals the viewport during reading.
  - Focus the transcript row after seek: rejected because pointer and keyboard context should stay with the playback control.

## Decision 4: Separate stable speaker key from display name

- **Decision**: Add a provider-neutral `speaker_key` to transcript review rows and keep it stable while an optional meeting-local display name changes `speaker_label` presentation.
- **Rationale**: Timeline activity, transcript linkage, and persistence need an identity that does not change when a user renames the speaker.
- **Alternatives considered**:
  - Use the visible label as identity: rejected because renaming would break DOM and persistence joins.
  - Mutate imported diarization labels: rejected because provider-originated result truth must remain recoverable.

## Decision 5: Persist one meeting-scoped override row

- **Decision**: Store at most one display-name row per workspace/meeting/speaker key. Query it with meeting review, project it onto transcript/lanes, and delete it with diarization-derived meeting content.
- **Rationale**: Reload persistence is explicit user value. A small override avoids transcript revision machinery while preserving imported rows and a clean future upgrade path.
- **Alternatives considered**:
  - Browser storage: rejected because it is device-local, unaudited, and inconsistent between browser and embedded app.
  - Full transcript revision/optimistic-edit subsystem: rejected because merge/split and text editing are outside scope.

## Decision 6: Reuse existing authorization, audit, and form patterns

- **Decision**: Permit creator or workspace owner/admin edits through authenticated CSRF-protected browser/desktop form routes. Reuse processing audit events with only action and speaker key metadata; never store the display name in audit metadata.
- **Rationale**: This preserves current trust boundaries and gives accountable mutation without duplicating policy or content in logs.
- **Alternatives considered**:
  - Allow every viewer to rename: rejected because a shared meeting label is durable team-visible content.
  - Add a new public JSON mutation API: rejected because the requested surfaces already use one server-rendered form path.
