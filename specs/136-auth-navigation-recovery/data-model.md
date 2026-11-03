# Data Model: Cabinet navigation lifecycle

## Stable document

| Field | Rule |
|---|---|
| URL | Разрешён существующей route policy и безопасен для повторного открытия. |
| Method | Только GET. |
| Auth routes | Только корневые `/login` и `/sign-up`; action subpaths не являются stable document. |
| Use | Может стать `currentRoute`, declarative request identity и history item. |

## Transient navigation

| Field | Rule |
|---|---|
| Origin | POST action, external OAuth provider, callback или nested auth action. |
| Persistence | Не записывается в `currentRoute` и не заменяет declarative request identity. |
| History | Не доступна через Forward/Reload; Back ищет предыдущий stable document. |
| Recovery | После restart/remount возвращается на последний stable document, не воспроизводит action. |

## OAuth continuation

| State | Entered by | External provider allowed | Session presentation |
|---|---|---|---|
| none | normal stable document | no | current stable state |
| primarySignIn | login/signup start | yes | auth-required до protected stable page |
| providerLink | approved Settings provider-link start | yes | existing authenticated state remains |

## Session boundary

| Transition | Required behavior |
|---|---|
| unauthenticated → protected stable document | Commit new stable route/identity, then erase prior history. |
| protected → stable login/signup document | Commit safe auth route/identity, then erase prior history. |
| 401 or workspace reselection | Fail closed immediately; recovery starts from safe login/reselection route. |
| transient navigation | Do not remount or erase history merely because it is POST/OAuth. |

## Уточнение текущего среза 2026-10-17

Обычный POST настроек с 200, ошибкой или отменой не означает смену сессии.
Не повторять POST как GET; отложенная успешная граница применяется только
после сохранения стабильных route/request identity. 401/выбор пространства
сразу закрывают прежнюю историю. Устаревший callback не применяет границу
к новой навигации. OAuth provider-link остаётся требованием всей F136 и
не считается реализованным текущим срезом T005/T006/T010.
