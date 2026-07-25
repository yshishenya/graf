# UI contract: settings IA

## Canonical routes

| Surface | Browser | Embedded desktop | Notes |
|---|---|---|---|
| Overview | `/settings` | `/desktop/settings` | Global navigation target |
| Recording | `/settings/recording` | `/desktop/settings/recording` | Native handoff only |
| Summary formats | `/settings/summaries` | `/desktop/settings/summaries` | Existing summary API remains unchanged |
| Workspace and team | `/settings/workspace` | `/desktop/settings/workspace` | Existing spaces/offers actions |
| Account and security | `/settings/account` | `/desktop/settings/account` | Safe provider/device projection |
| Calendars | `/settings/integrations/calendar` | `/desktop/settings/integrations/calendar` | Existing integration contract |
| Provider-link confirmation | `/settings/provider-links/:id` | `/desktop/settings/provider-links/:id` | Existing flow, return link points to account |

`/settings/spaces`, `/settings/join-offers` and existing calendar action routes
remain compatible. New settings pages do not accept an arbitrary redirect URL;
return targets are a fixed allowlist.

## Navigation contract

- The global «Настройки» item points to the overview.
- The overview has one primary `<h1>Настройки`.
- Every category has one `<h1>`, a visible path back to overview, and a shared
  inner navigation with `aria-current="page"`.
- Categories are not rendered as empty placeholders.
- Admin links remain outside this navigation.

## Scope vocabulary

Use only these labels unless a new product decision adds a term:

`Личная настройка`, `В этом пространстве`, `Только владелец`, `На этом Mac`,
`Только в браузере`, `Только в приложении`.

## Mutation states

Grouped forms expose `pristine`, `dirty`, `saving`, `saved` and `error` through
accessible status text. On error, values remain in the form and secrets are
never echoed. Destructive device/calendar actions require explicit confirmation.

## Accessibility contract

- Use semantic headings, links, buttons, labels and fieldsets.
- Dialogs use native modal semantics where available, have an accessible name,
  support Escape/close, return focus to the opener and move focus to the first
  useful field on open.
- Status/errors use `role="status"` or `role="alert"` with concise Russian copy.
- Focus styles remain visible; keyboard-only navigation reaches every action.
