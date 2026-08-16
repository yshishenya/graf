# Research: Источник системного звука в индикаторе записи

## Decision 1: Reuse the approved session source metadata

- **Decision**: The indicator reads the source display name already carried in the current `CaptureSession` evidence.
- **Rationale**: `TwoBrainRecApp.startManualRecording` records the approved scope name before capture starts; detector-assisted recording uses the verified meeting target name. This is the existing source of truth and does not add work to audio callbacks.
- **Alternatives considered**: Polling running applications, inspecting each audio frame, or adding a new ScreenCaptureKit attribution layer. These would be less truthful for display-wide system audio, add privacy/performance surface, and are outside the requested UI feature.

## Decision 2: Use explicit neutral fallbacks

- **Decision**: Map the existing manual sentinel (`Current display/system audio`) to «Системный звук»; missing, empty, or invalid values map to «Источник не определён».
- **Rationale**: The current MVP captures system audio from the approved display scope and cannot always attribute a frame to one application. The UI must not imply a more precise attribution than the capture contract provides.
- **Alternatives considered**: Guessing the frontmost app or showing the last detected meeting app. Both can be false during manual capture or after a target changes.

## Decision 3: Keep the source inside the existing status surface

- **Decision**: Add one compact source row below the primary status and above the existing actions, with the status and Stop action retaining visual priority.
- **Rationale**: The user asked for the upper recording indicator; reusing its material card avoids a second banner and preserves the existing one-action Stop affordance.
- **Alternatives considered**: A new toolbar badge or a separate settings surface. Those make the information slower to find and duplicate capture UI.

## Decision 4: Treat accessibility as a first-class source contract

- **Decision**: The source row gets a stable accessibility identifier, a combined label containing the full source, and a help string; visual truncation is allowed.
- **Rationale**: App names can be long and the capture pane has a bounded width. Full semantic text must remain available without requiring layout expansion or animation.
- **Alternatives considered**: Letting the text wrap or relying on a visual-only tooltip. Both are less predictable for narrow windows and VoiceOver users.

## Decision 5: No persistence or telemetry change

- **Decision**: Do not add a manifest field, server contract, diagnostic field, or analytics event.
- **Rationale**: The feature is an active local indicator, not a new recording fact. Existing metadata already supports the presentation and privacy boundary.
- **Alternatives considered**: Persisting source history or emitting source-change events. Neither is needed for the requested behavior and would expand privacy and deletion obligations.
