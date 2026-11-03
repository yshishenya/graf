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

### Продолжение OAuth, T004/T011/T012 — 2026-10-28

Разрешение действует только в текущем присоединённом WebView. Оно выбирается
до отправки одобренного main-frame действия и передаётся общим controller и
coordinator при обработке настоящего завершения документа.

| Событие | Продолжение и обязательный результат |
|---|---|
| POST на точный same-origin `/desktop/settings/provider-links/{provider}/start` из текущего завершённого авторизованного Settings | `providerLink`; начальный и исходный документы принадлежат тому же origin, source/target — main frame; путь без кодирования разделителей, query и fragment; provider принят действующей route policy. |
| Начало существующего входа из login/signup | `primarySignIn`; не смешивается с подключением провайдера. |
| Внешний HTTPS или callback в текущем продолжении | Сохраняет выбранный тип; документ transient, не становится route/Reload/history target. `providerLink` не устанавливает sessionExpired и не создаёт boundary. |
| Возврат на стабильный защищённый документ | Сначала route/request identity и presentation; `primarySignIn` применяет новую границу, `providerLink` сохраняет прежнюю. Затем разрешение внешнего OAuth снимается. |
| Корневой login/signup, включая logout | Приоритет обычной auth-границы над `providerLink`; прежняя защищённая история недоступна. |
| 401 или workspace reselection | Немедленная блокировка прежней истории, сброс продолжения; providerLink не маскирует потерю сессии. |
| Текущая отмена/ошибка/запрещённый переход, замена самостоятельной навигацией вне цепочки, detach или завершение процесса WebKit | Сброс продолжения без повторного POST; восстановление только по существующим safe-document guards. Redirect и внутреннее добавление headers не считаются самостоятельной заменой. |
| Устаревший callback прежней навигации | Не меняет ни новое продолжение, ни границу, ни документ. |

Прямой GET к start, запрос из неподтверждённого/чужого документа и callback
без текущего продолжения не открывают доступ к внешнему провайдеру.
Платёжная цепочка и скачивания сохраняют собственные существующие ограничения;
они не получают auth-разрешение. Сервер проверяет подлинность привязки как прежде.

- Reload and Forward are disabled whenever their target is transient or belongs
  to a prior protected session.
- Back may jump over transient entries to the nearest permitted stable entry.
- No diagnostic event includes credential, code, cookie or meeting-content data.

## Уточнение среза 2026-10-17 (история)

Обычный POST настроек с 200, ошибкой или отменой не означает смену сессии.
Не повторять POST как GET; отложенная успешная граница применяется только
после сохранения стабильных route/request identity. 401/выбор пространства
сразу закрывают прежнюю историю. Устаревший callback не применяет границу
к новой навигации. OAuth provider-link остаётся требованием всей F136 и
не считается реализованным текущим срезом T005/T006/T010.
