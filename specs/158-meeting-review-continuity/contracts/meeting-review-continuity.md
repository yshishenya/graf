# UI Contract: Meeting Review Continuity

## Shared surfaces

The browser meeting detail and embedded `/desktop/meetings/<id>` surface MUST
render the same contract from the shared cabinet template/static assets.

## Speaker timeline

When playable audio and at least one lane are available:

- a wrapper has `data-speaker-timeline-shell`;
- the rows remain under `data-speaker-timeline`;
- the resize boundary has `data-speaker-timeline-resize`, `role="separator"`,
  `aria-orientation="horizontal"`, `tabindex="0"`, bounded value attributes,
  and `aria-controls` pointing at the timeline;
- the boundary is omitted/hidden when all rows fit the default height;
- a visible `data-speaker-timeline-hint` describes lane-to-playback navigation;
- each track has `data-timeline-track`, `role="button"`, `tabindex="0"`, and an
  action-oriented accessible name.

When audio or diarization is unavailable, the interactive hint and resize
boundary MUST NOT claim that a non-interactive lane can be used.

## Speaker rename

Each editable rename form has `data-speaker-name-form` and a stable
`data-speaker-key`. On a successful response, the client updates only matching
speaker label/name nodes and form value in the current detail DOM. It MUST NOT
call a full page reload for this success path or replace the audio element.

On a non-recoverable save error, the form retains the last confirmed label and
exposes `data-speaker-name-error` with a retryable action. Existing recovery
helpers remain authoritative for login/access/unavailable responses.

## Meeting tabs

The existing `role="tablist"`, two `role="tab"` controls, two
`role="tabpanel"` panels, `aria-selected`, `aria-controls`, hash values, and
keyboard behavior remain unchanged. The tablist receives only a sticky visual
class and safe scroll margins for source targets.
