# Data Model: Источник системного звука в индикаторе записи

## Existing source evidence

The feature does not introduce a new persisted entity. It consumes the existing per-session evidence entry:

| Field | Meaning | Presentation rule |
|---|---|---|
| `sourceDisplayName` | Approved display name for the current capture scope | Trim whitespace; known target names are shown as-is |
| `Current display/system audio` | Existing manual-recording sentinel | Show «Системный звук» |
| missing/blank/unknown | No trustworthy attribution | Show «Источник не определён» |

## Lifecycle

1. The source is present when the capture session reaches preparation/ready state.
2. The same value remains visible through starting, active, paused, degraded, and stopping states.
3. The source row is not presented as active-source truth after the session returns to an idle state; the existing saved-state label remains authoritative.

## Validation rules

- Do not infer a source from the frontmost application or from audio levels.
- Do not display an empty or whitespace-only name.
- Do not mutate the source evidence from the view.
- Do not persist or export a new source value.
