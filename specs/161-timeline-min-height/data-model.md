# Data Model: Минимальная высота таймлайна спикеров

Изменений в постоянной модели данных нет.

## Presentation state

| Поле | Источник | Ограничение |
|---|---|---|
| `defaultHeight` | текущий markup/JS contract | `120px`, нижняя граница |
| `currentHeight` | transient DOM state | от `defaultHeight` до bounded maximum |
| `contentHeight` | rendered timeline scroll height | не меньше `defaultHeight` |
| `viewportHeight` | текущая геометрия playback shell | ограничивает ручное расширение |

Имя и сегменты спикеров остаются существующими безопасными view-моделями;
никакие пользовательские данные не записываются.
