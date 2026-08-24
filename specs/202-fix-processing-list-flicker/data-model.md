# Data Model: Стабильные статусы обработки

Новых persistent entities и миграций нет.

## Existing state ownership

| State | Owner | UI use |
|---|---|---|
| Meeting list presentation status | Server list response | Structure, status kind, terminal truth |
| Processing status projection | Content-safe processing API | Temporary text for a server-marked processing row |
| Meeting-list generation | Browser runtime | Reject detached/stale responses |
| Projection fetch timestamp | Browser runtime | 15-second per-meeting throttle |

## Transition contract

`submitted/processing -> processed|blocked|failed_terminal|canceled` triggers one
authoritative list refresh. Intermediate projection changes stay within the
same processing row. Failed/terminal rows do not enter projection polling.
