# Calendar tray contract

## Purpose

The macOS menu-bar surface is an upcoming/context view, not a second calendar
application. It mirrors the server-owned calendar projection used by the
browser and embedded cabinet.

## Read path

```text
NSStatusItem -> CalendarTrayModel
  -> DesktopUploadClient.listDesktopCalendarUpcoming(
       beforeMinutes: 15, afterMinutes: 1440)
  -> GET /api/v1/desktop/calendar/upcoming
  -> existing desktop auth cookie + tenant/session policy
```

The model is in-memory only, renders at most 12 events, sorts by start time,
and uses `DesktopCalendarPromptEvent.safeDisplayTitle()`. It does not persist
event rows, credentials, URLs or provider payloads.

## States and copy

| State | User-facing result |
|---|---|
| loading | `Обновляем…` / `Загружаем календарь…` |
| loaded | upcoming rows and last safe projection |
| empty | `Нет ближайших встреч` |
| needsSignIn | `Войдите в GRAF, чтобы увидеть встречи` |
| unavailable | `Календарь временно недоступен` |
| stale | `Показаны последние данные` and `Последнее обновление не удалось` |

The view includes `Открыть GRAF`, `Настройки календаря` and a refresh action.
No message exposes provider response text, raw event title, attendee email,
meeting URL or credential state.

## Explicit actions and prohibitions

- `Открыть встречу` is shown only for a server-projected HTTP(S) link and only
  after a direct user click.
- The tray never auto-joins, auto-records, sends a bot, changes a calendar or
  controls native Record/Stop.
- Browser and embedded navigation use the existing session bridge and route
  policy. They do not receive provider secrets from the tray.
- Refresh happens on app activation, auth-session change, system wake and a
  60-second bounded timer; no unbounded polling or provider request is made.

## Accessibility

The status item has an accessible label, the popover has a named container,
refresh is labeled and disabled during loading, event rows expose safe title
and time, and action buttons have explicit Russian labels. The visual state
must not be the only indication of loading, stale or unavailable data.
