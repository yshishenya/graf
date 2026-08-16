# UI Contract: Recording Source Indicator

## Surface

The existing upper recording status card contains:

1. Primary recording state and visible-indicator icon.
2. A compact source row labelled «Источник».
3. Existing pause/resume and one-action Stop controls.

The source row is informational only and has no click action.

## Source states

| Evidence | Visible value | Accessibility value |
|---|---|---|
| Known verified target | target display name | «Источник: `<full name>`» |
| Manual system-audio scope | «Системный звук» | «Источник: системный звук» |
| Missing/invalid evidence | «Источник не определён» | «Источник: источник не определён» |

## Layout and accessibility

- The row is single-line visually and may truncate long names.
- The full value is available to VoiceOver and the system help tooltip.
- The row has a stable identifier: `systemAudio.status.source`.
- It must remain readable in increased contrast and must not depend on motion.
- The source row must not reduce or merge the existing Stop, Pause, or Resume actions.
