# Research: Продуктовый раздел настроек

## Existing Product Surface

- The cabinet already exposes `/settings`, `/settings/recording`, `/settings/summaries`, `/settings/workspace`, `/settings/account`, `/settings/notifications`, and `/billing`.
- `settings_category_navigation()` in `cabinet/view_models.py` is the existing source for labels, scope, descriptions, groups, icons and routes.
- `render_settings_page()` selects the existing page template by category and injects CSRF, account, workspace, notification and billing projections.
- `settings_navigation.html` already emits `aria-current="page"` for the selected category.
- Existing settings templates have no client-local persistence; mutations submit to server routes and support no-JavaScript operation.

## Design Reference Findings

- The Open Design reference uses a dark graphite work surface, thin dividers, restrained radii, scope-first labels, a two-column overview on desktop and a one-column stack on mobile.
- The most important product boundary is explicit copy: recording is configured in the native macOS app; web settings do not control active capture.
- Billing unavailable/gated states must remain explicit and must not use fabricated figures.

## Decisions

| Decision | Reason |
|---|---|
| Reuse server routes and projections | Avoid duplicate settings truth and preserve auth/CSRF/tenant boundaries |
| Keep Jinja/HTMX cabinet | Existing product architecture already supports the flow and no SPA is required |
| Tune settings-only CSS | Visual parity can be reached without changing the broader product shell |
| No migration | All requested settings data already exists or is intentionally unavailable/gated |

## Rejected Alternatives

- Copying the Open Design standalone HTML into the product: would create fake localStorage state and bypass server truth.
- Adding a new settings API or client store: unnecessary and risks duplicate account/workspace state.
- Reviving recording controls in the web cabinet: conflicts with the macOS capture boundary.
