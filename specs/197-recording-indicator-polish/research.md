# Research: Деликатный индикатор источника записи

## Evidence from the current surface

- The provided screenshot shows one prominent recording capsule with the status,
  elapsed time, Pause and Stop actions. The primary attention target is already
  correct; adding another capsule would make the hierarchy noisier.
- `RecordingTitlebarHUD` currently renders status, timer and actions but no source
  text. `CaptureStatusItem` already normalizes the approved `CaptureSession`
  evidence into a display name and truthful fallbacks.
- The existing source row is in the sidebar status surface, so the requested
  upper indicator is missing its most important context. The smallest root-cause
  fix is to move that presentation to the titlebar HUD and remove the duplicate
  sidebar row.

## Decision 1: Reuse session evidence, not live app detection

- **Decision**: Read the existing `CaptureStatusItem.sourceDisplayName(for:)`
  result and its accessibility label.
- **Rationale**: The value is already approved at session start. Polling running
  applications or inspecting audio frames would imply a precision the current
  display-wide system-audio capture contract does not guarantee, while adding
  privacy and performance surface.
- **Alternative rejected**: A new process observer or ScreenCaptureKit attribution
  layer is outside this presentation-only fix.

## Decision 2: One outer surface, inline secondary text

- **Decision**: Keep the existing capsule, status icon and control geometry. Add a
  quiet single-line source label in the same status group: `Источник · Zoom`.
  Manual system audio remains `Системный звук`; missing evidence remains
  `Источник не определён`.
- **Rationale**: A same-row secondary label preserves the 44-point strip height,
  keeps the primary state dominant, and makes the requested information visible
  at a glance without creating a second panel or a clickable badge.
- **Alternatives rejected**: A second row would increase the titlebar footprint;
  a new badge, app icon, or source button would compete with Pause/Stop and imply
  an interaction that does not exist.

## Decision 3: Truncate visually, preserve the full semantic value

- **Decision**: Keep the visual source text to one line with tail truncation and a
  bounded width. Expose the full `Источник: <name>` value through accessibility
  label and the native help tooltip.
- **Rationale**: Long or localized app names must not push Stop out of the HUD or
  force a titlebar reflow. VoiceOver and help remain useful when the visual copy
  is shortened.
- **Alternative rejected**: Wrapping or reducing all controls to fit a long name
  would weaken the persistent-stop gate.

## Decision 4: Keep the source informational and non-interactive

- **Decision**: No source click action, app icon, source selector, persistence,
  telemetry, network call, or capture-route change.
- **Rationale**: The user asked for calm status context, not a new recording
  control. This keeps the change inside the existing local capture indicator and
  its privacy boundary.

## Design references

- [Apple Human Interface Guidelines — Status bars](https://developer.apple.com/design/human-interface-guidelines/status-bars): use a status surface for concise, glanceable state information.
- [Apple Human Interface Guidelines — Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons): preserve clear action hierarchy and avoid making informational text look actionable.
- [Apple Human Interface Guidelines — Focus and selection](https://developer.apple.com/design/human-interface-guidelines/focus-and-selection): retain distinct, discoverable controls and accessible focus/labels.
- [Apple Human Interface Guidelines — Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility): keep semantic information available beyond visual styling and truncation.

These references guide hierarchy and interaction boundaries; the final visual
style continues to use GRAF's existing colors, typography, spacing and native
macOS surface rather than copying another product.
