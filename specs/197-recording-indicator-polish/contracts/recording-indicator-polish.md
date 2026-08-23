# UI Contract: Деликатный индикатор источника записи

## Surface

The existing native titlebar recording HUD remains one outer capsule containing:

1. The primary visible recording state and icon.
2. A compact elapsed-time value.
3. The existing Pause/Resume and one-action Stop controls.

The source is an informational, single-line child of the primary status group.
It has no background, border, icon, click action, or source-selection behavior.

## Visible source values

| Normalized evidence | Visible value |
|---|---|
| Known verified target `Zoom` | `Источник · Zoom` |
| Manual system-audio scope | `Системный звук` |
| Missing, blank, or invalid evidence | `Источник не определён` |

The source is shown only while the current capture session is in an active
indicator lifecycle state. It must not remain as an active-source claim after
the session is stopped or finalized.

## Layout and accessibility

- The source stays on one line and uses tail truncation within a bounded width.
- The source is visually secondary to the recording state and controls.
- The full normalized value is exposed as `Источник: <value>` through the
  source accessibility label and native help tooltip.
- The stable identifier is `systemAudio.status.source`.
- The source must not reduce, merge, move, or disable Pause, Resume, or Stop.
- The HUD remains visible in increased contrast and does not depend on motion.
