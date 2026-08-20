# Contract: embedded navigation после изменяющей формы

## Вход

Main-frame navigation внутри разрешённого same-origin desktop route.

## Инварианты

1. `GET` document MAY обновить SwiftUI `currentRoute` и request identity.
2. `POST` и любой другой non-GET MUST remain WebKit-owned и MUST NOT
   автоматически воспроизводиться как GET.
3. Direct HTML response от email start/verify MUST remain visible until user
   action or terminal auth result.
4. Локализованный HTML response этих form endpoints при 4xx/5xx MUST remain
   visible; unrelated settings failures MUST retain the existing policy.
5. Redirect на разрешённый конечный GET MUST become the new SwiftUI route.
6. SwiftUI MUST NOT start a duplicate load while WebKit is already navigating
   to that final document.
7. Same-origin desktop headers, cookies, CSRF, rate limits, one-time codes and
   account-link rules MUST remain unchanged.
8. Email, code, token, nonce and private identifiers MUST NOT enter route,
   diagnostics or committed evidence.

## Production-like evidence

Один пользовательский submit создаёт один POST и не создаёт автоматический
`GET /desktop/settings/account/email-link/start`. Для этого пути нет 405,
экран кода остаётся в embedded WebView, а после успешной проверки выполняется
один конечный GET страницы аккаунта без пустого промежуточного экрана.
