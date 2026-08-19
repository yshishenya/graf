# UI Contract: Адаптивная высота таймлайна

- `data-speaker-timeline-default-height="120"` — безопасный базовый размер для
  трёх и более дорожек.
- `.speaker-timeline` в CSS имеет естественную высоту и bounded
  `max-height: 120px` до применения transient resize; фиксированный `height`
  не должен создавать пустое место для 1–2 дорожек.
- Для 1–3 дорожек resize separator скрыт, а `aria-valuemin/max/now` отражают
  естественный размер.
- Для 4+ дорожек separator доступен; `aria-valuemin` равен 120, а
  `aria-valuemax` равен минимуму полной высоты содержимого и viewport ceiling.
- Pointer и keyboard resize используют существующие `pointerdown/move/up`,
  `ArrowUp`, `ArrowDown`, `Home`, `End` semantics.
- Resize не меняет `audio.currentTime`, audio element, active lane или playback
  state.
