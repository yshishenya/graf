# Data Model: Адаптивная высота таймлайна спикеров

Постоянной модели данных нет.

## Presentation state

| Поле | Источник | Ограничение |
|---|---|---|
| `defaultHeight` | markup/JS contract | `120px`, базовый размер для 3+ дорожек |
| `naturalHeight` | rendered timeline geometry | фактическая высота строк до transient clamp |
| `minimumHeight` | natural height и число дорожек | natural для 1–3, `defaultHeight` для 4+ |
| `currentHeight` | transient DOM state | от `minimumHeight` до bounded maximum |
| `contentHeight` | rendered timeline scroll height | полная высота всех строк |
| `viewportHeight` | playback shell geometry | не вытесняет нижний playback bar |

Имена, сегменты и позиция audio element остаются существующими view/runtime
данными и этой функцией не изменяются.
