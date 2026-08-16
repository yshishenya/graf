# UI Contract: Product Settings Surface

## Navigation

- The overview contains the seven supported settings categories from `settings_category_navigation()`.
- The settings rail starts with a separate `Обзор` link to `/settings` (or `/desktop/settings`) before the four grouped category sections.
- Every category card and rail link resolves to its existing server route.
- The active rail item has both a visual selected state and `aria-current="page"`.

## Scope Copy

- `На этом Mac`: native recording and app-local controls.
- `В этом пространстве`: summaries default and workspace/billing state.
- `Личная настройка`: calendar selection, account/security and optional notifications.

## Trust Boundaries

- Browser settings do not control microphone/system-audio capture or active recording.
- Billing shows confirmed state only; unavailable/gated state is explicit.
- Account and workspace actions stay server-backed and preserve CSRF/session/tenant checks.

## Responsive Contract

- Desktop uses a navigation rail and content column.
- At 390px the rail and content stack without document-level horizontal overflow.
- All interactive elements have visible keyboard focus.
