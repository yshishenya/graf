# Contract: embedded cabinet support bridge

## Inputs

- A `DesktopSupportIncidentReport` already generated from the local safe-report model.
- The configured same-origin `WKWebView` showing an authenticated cabinet document.

## Required boundary

1. Swift serializes the report as data and passes it through `callAsyncJavaScript` arguments.
2. A fixed script reads the document's existing CSRF meta value and runs a fixed same-origin `fetch` endpoint with `credentials: "same-origin"`.
3. WebKit owns the session cookie and CSRF token throughout. Swift receives only the bounded HTTP status and response/problem code.
4. The bridge rejects an absent, external, login or unauthenticated cabinet surface with a safe auth-required category.

## Forbidden behaviour

- Copying cookies from `WKHTTPCookieStore` to `HTTPCookieStorage` for support intake.
- Adding a `Cookie`, `Authorization`, `X-Auth-Session` or CSRF header from native code.
- String interpolation of report fields into JavaScript source.
- Logging the report body, browser page contents, token, cookie or CSRF value.

## Failure mapping

| Condition | Bounded desktop result |
|---|---|
| No signed-in cabinet or missing CSRF document marker | `support_incident.auth_session_required` |
| Same-origin network failure | `network_unavailable` |
| Server rejected report | server problem code only |
| Server accepted, Issue pending | successful `pending_sync` response |
