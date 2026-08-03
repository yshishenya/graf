# UI Contract: meeting-summary-ux

## Stable DOM contract

- One root element MUST expose `data-outcome-source-basis`.
- Exactly one element per category MUST expose
  `data-outcome-category` and `data-outcome-state` for:
  `summary`, `key_points`, `decisions`, `action_items`, `followups`, `risks`,
  `questions`, `evidence`.
- An available item uses `.outcome-item`; its text is escaped server-side.
- Optional metadata uses explicit data attributes/classes and is rendered only
  when the stored field is non-empty.
- A source control uses `button[type="button"][data-seek-seconds]`, displays a
  localised timecode and has a non-empty `aria-label`.
- Secondary categories live inside one native `.notes-more` disclosure and do
  not compete with the primary summary view when closed.
- Non-available categories do not render `.outcome-item` content.

## Information architecture

```text
meeting header/status
└── detail tabs
    ├── Итоги
    │   ├── Кратко
    │   ├── Действия
    │   ├── Решения
    │   └── Дополнительные разделы (раскрываемый блок)
    └── Расшифровка
        └── existing transcript + persistent player
```

## Interaction contract

- Clicking a detail tab changes `aria-selected`, `hidden`, focusability and URL
  hash without a full page request.
- Clicking a source control reuses the existing playback listener and never
  sends transcript/audio directly from the browser to a provider.
- Existing meeting Share/Export controls remain the single save/share entry
  point; the summary does not add a second inline export CTA.
- Summary format/candidate controls retain their existing explicit preview and
  acceptance semantics.

## Accessibility contract

- Headings form a meaningful `h2`/`h3` hierarchy.
- State meaning is written text, not color-only.
- Buttons have labels, focus-visible styles and touch-safe hit area.
- Long text wraps; mobile view has no horizontal overflow.
- Async candidate/format status remains `role="status"`/`aria-live` as today.
