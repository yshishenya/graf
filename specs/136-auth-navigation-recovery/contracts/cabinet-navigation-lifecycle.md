# Contract: Cabinet navigation lifecycle

## Boundary

This is an internal macOS UI contract. Server HTTP routes, cookies, headers and
provider protocols are unchanged.

## Invariants

1. A `currentRoute` is always a stable document or absent.
2. A transient request can remain visible in WebKit but cannot become a future
   SwiftUI GET request.
3. Every navigation surface — native buttons, browser gestures, `updateNSView`
   and automatic recovery — uses the same replay-safe predicate.
4. External OAuth is permitted only during a registered primary sign-in or an
   approved authenticated provider-link continuation.
5. A session boundary is committed after the target stable document has been
   recorded, never while a one-shot action is in flight.

## Transition table

| From | Event | Result | Persisted route | History action |
|---|---|---|---|---|
| stable login | email POST | verification UI | login | action unsafe |
| stable login | provider start → external → callback | provider/callback UI | login | legs unsafe |
| primary sign-in | protected stable page | ready cabinet | protected page | erase pre-login history |
| protected settings | provider-link POST → external → callback | provider link UI/result | settings until final result | legs unsafe; no session reset |
| protected page | logout → stable login | auth-required | login | erase protected history |
| any protected page | 401/reselection | recovery | safe auth/recovery route | deny prior protected history |

## Observable behavior

- Reload and Forward are disabled whenever their target is transient or belongs
  to a prior protected session.
- Back may jump over transient entries to the nearest permitted stable entry.
- No diagnostic event includes credential, code, cookie or meeting-content data.

## Уточнение текущего среза 2026-10-17

Обычный POST настроек с 200, ошибкой или отменой не означает смену сессии.
Не повторять POST как GET; отложенная успешная граница применяется только
после сохранения стабильных route/request identity. 401/выбор пространства
сразу закрывают прежнюю историю. Устаревший callback не применяет границу
к новой навигации. OAuth provider-link остаётся требованием всей F136 и
не считается реализованным текущим срезом T005/T006/T010.
