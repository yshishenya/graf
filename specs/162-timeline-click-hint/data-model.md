# Data Model: Понятная подсказка на таймлайне

Изменений постоянной модели данных нет.

## Presentation contract

| Element | State | Rule |
|---|---|---|
| Inline playback hint | playable | exactly one copy before the timeline |
| Inline playback hint | unavailable/empty | absent; existing truthful status remains |
| Track control | playable | focusable seek control with aligned accessible name |
| Hint layout | narrow viewport | wraps without horizontal overflow |
