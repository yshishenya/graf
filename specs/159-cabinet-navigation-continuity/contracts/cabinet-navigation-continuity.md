# Contract: cabinet navigation continuity

## Shared shell contract

Browser and embedded pages use the same server-rendered component contract. The
only surface difference is the explicit `embedded` route prefix and native-owned
update affordance.

### Sidebar toggle

- Exactly one element matches `[data-cabinet-rail-toggle]` per shell.
- It is a `button[type="button"]` with `aria-controls="cabinet-sidebar"`.
- `aria-expanded="true"` means the rail is visible and the accessible action is
  «Скрыть боковую панель»; `false` means the action is «Показать боковую
  панель».
- Pointer, Enter and Space use the same activation path.
- The button keeps a stable position and focus after the state change.
- Re-running shell initialization after HTMX/partial updates is idempotent.

### Search

- Search icon is decorative (`aria-hidden="true"` or equivalent) and does not
  receive pointer events.
- Input text has explicit inline space from the icon and any clear action.
- The contract is checked for empty, Russian typed, loading, disabled, focus and
  narrow states without document horizontal overflow.

### Download CTA

- Ordinary browser cabinet shell contains exactly one focusable sidebar link to
  `/download` when the public destination is available.
- Embedded cabinet shell contains zero sidebar links to `/download`.
- Meeting audio/content download actions are unrelated and must not be counted as
  the shell CTA.

### Profile menu

- One profile trigger contains only safe name/email projection and opens a
  compact menu.
- Menu actions are exactly profile information, «Настройки» and the existing
  CSRF-protected logout action.
- Escape and outside click close the menu; focus returns to the trigger.
- Missing/long values wrap within the rail; no provider subject, internal ID or
  token appears in rendered HTML.

## Settings contract

- Each settings page has exactly one visible accessible primary settings rail.
- Existing category ids and hrefs remain the source of truth.
- The selected category has one `aria-current="page"` in the primary rail.
- A canonical «К встречам» link targets `/meetings` or `/desktop/meetings`.
- Existing forms, CSRF fields, role/billing gates, calendar handoff and native
  recording boundary are unchanged.

## Auth contract

- Normal unknown-email login does not silently create an account.
- Explicit `/sign-up`, invitation/provider and email-code routes remain
  reachable where supported.
- Browser and embedded surfaces preserve the same outcome meaning, safe return
  paths and Russian error copy.
- CSRF, state/nonce, exact-email, rate-limit, session, tenant and account-linking
  semantics are not changed by the shell work.

## Evidence contract

Allowed evidence is synthetic markup, source markers, safe counts, route names,
viewport/state labels, command output and exact SHA. Do not store credentials,
tokens, real meetings, transcripts, audio, signed URLs, private screenshots or
real account identifiers.
