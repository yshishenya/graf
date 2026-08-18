# UI Contract: Минимальная высота таймлайна

- `data-speaker-timeline-default-height="120"` — единая базовая высота.
- `.speaker-timeline` имеет `height` и `max-height` не меньше `120px` до
  применения transient resize.
- Resize separator сообщает `aria-valuemin="120"` и не превышает
  `min(contentHeight, viewportHeight)`.
- При 1–3 дорожках separator скрыт, если полная высота контента помещается в
  базовый размер; при overflow он доступен.
- Pointer и keyboard resize используют существующие `pointerdown/move/up`,
  `ArrowUp`, `ArrowDown`, `Home`, `End` semantics.
