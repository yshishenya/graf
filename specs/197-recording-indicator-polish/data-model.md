# Data Model: Деликатный индикатор источника записи

## Existing entity: `CaptureSession`

No new entity or persisted field is introduced.

| Field | Existing role | Presentation use |
|---|---|---|
| `state` | Current capture lifecycle state | Determines whether the active source label is present. |
| `triggerEvidence["sourceDisplayName"]` | Approved session-level source evidence | Supplies the known app name or manual sentinel. |
| `stopActionAvailable` | Existing control availability | Remains independent of source text and preserves one-action Stop. |

## Derived presentation values

`CaptureStatusItem` remains the single normalization point:

- known non-empty app name → the trimmed display name;
- `Current display/system audio` → `Системный звук`;
- missing, blank, or invalid evidence → `Источник не определён`;
- `idle`, `stopped`, `failed`, and `finalized` → no active source presentation.

The top HUD derives the visible copy from that normalized value:

- known app → `Источник · <display name>`;
- manual or unknown fallback → the fallback text itself.

The full accessibility value remains `Источник: <normalized value>` and is not
truncated. Source presentation is read-only and lasts only for the current
capture session.

## State coverage

The normalized source helper continues to understand `detecting` and `ready`,
but the upper titlebar HUD is present only for `starting`, `active`, `paused`,
`degraded`, and `stopping`, matching the existing strip lifecycle. In those HUD
states the source remains stable. It disappears once the session is no longer
an active capture surface. No state transition or capture callback is changed
by this feature.
