# Research: Единый ввод одноразового кода

## Инвентаризация

| Контекст | Route/render flow | Surface | Source of truth |
|---|---|---|---|
| Login | `/login/email/start` → `flow=login` | web and desktop WebView | `cabinet/auth/email_code.html` |
| Signup | `/sign-up/email/start` → `flow=signup` | web and desktop WebView | `cabinet/auth/email_code.html` |
| Share invitation | login verify context → `flow=share_invitation` | web and desktop WebView | `cabinet/auth/email_code.html` |
| Browser account link | `/settings/account/email-link/start` → `flow=link` | web | `cabinet/auth/email_code.html` |
| Desktop account link | `/desktop/settings/account/email-link/start` → `flow=desktop_link` | macOS embedded WebView | `cabinet/auth/email_code.html` |

Search across `apps/server`, `apps/macos`, tests, and templates found one
email-code template and no native Swift OTP view. Feature 070's original
six-slot behavior was replaced by a single `data-code-input` in the auth-sync
commit; the current bug is therefore a shared regression, not five independent
screens.

## Decisions

- Keep the server-facing field named `code` and keep all route actions/hidden
  fields unchanged.
- Render six visible `data-code-slot` inputs plus one hidden `data-code-hidden`
  field. JavaScript composes the hidden value on every edit and before submit.
- Keep a `noscript` single-field fallback so disabling JavaScript does not make
  the form submit an empty code.
- Use CSS grid with six equal tracks and a single shared `--code-slot-size`
  capped by the auth content width. At 390px, the slots shrink while retaining
  a 1:1 ratio and no horizontal overflow.
- Let the existing macOS WebView consume the same HTML/CSS/JS. No Swift UI or
  route policy change is needed for the OTP component.

## Explicitly not changed

Email code generation, hashing, expiry, rate limits, callback state, CSRF,
provider verification, session issuance, and account merge logic remain server
behavior outside this slice.
