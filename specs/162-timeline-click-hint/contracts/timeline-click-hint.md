# UI Contract: Подсказка на таймлайне

- Playable speaker timeline renders exactly one `data-speaker-timeline-hint`.
- Visible copy is action/result oriented and contains «цветной фрагмент» and
  «перейти к этому месту записи».
- The hint is a paragraph/note, not a button and not a focus target.
- Each `[data-timeline-track]` remains `role="button"`, keyboard focusable and
  named with the seek action.
- Unavailable/empty playback markup does not render the hint.
- Repeated partial render produces one hint per timeline shell.
