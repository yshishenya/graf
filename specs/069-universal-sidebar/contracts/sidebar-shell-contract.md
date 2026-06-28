# Contract: Cabinet Sidebar Shell

## Scope

This contract applies to authenticated user cabinet full pages and desktop embedded cabinet full pages.

Out of scope:

- Admin pages.
- Authentication pages.
- Native desktop product navigation.

## Full Page Shell Contract

Every covered full cabinet page must expose:

- exactly one cabinet shell root;
- exactly one primary sidebar;
- exactly one page content region;
- exactly one active/current navigation destination;
- surface mode: standalone browser or desktop embedded.

Required user-facing behavior:

- The sidebar brand, navigation order, disabled states, counts, footer, and active state remain consistent across covered pages.
- The current destination is available to assistive technology on exactly one available navigation destination.
- The focus indicator remains visible and distinct from the selected destination state.
- Desktop embedded compact mode keeps destination accessible names even when labels are visually hidden.

## Navigation Destination Contract

Destination ids:

- `meetings`: meetings list and meeting detail pages.
- `settings`: settings and calendar settings pages.
- future/disabled ids may be visible but unavailable.

Destination mapping:

| Destination | Browser route | Desktop embedded route |
|-------------|---------------|------------------------|
| meetings | `/meetings` | `/desktop/meetings` |
| settings | `/settings/integrations/calendar` | `/desktop/settings/integrations/calendar` |

Rules:

- The destination id controls active state.
- Exactly one available destination is current in the primary sidebar.
- Disabled or future destinations are never current destinations.
- Route paths may differ by surface mode.
- Labels and disabled states must not differ by surface mode.

## Fragment Contract

Content fragments must expose only the content that the user requested to update.

Forbidden in fragments:

- cabinet shell root;
- primary sidebar;
- duplicate navigation landmark;
- duplicated rail toggle.

Required behavior:

- Meeting list filtering updates the meeting list/content region only.
- Settings fragment updates preserve the existing shell.
- A full page response may be used only when the client selects the intended content region and preserves one shell.

## Native Desktop Boundary

The native desktop app may own:

- capture controls;
- visible recording state;
- one-action stop;
- local custody/safety surfaces.

The native desktop app must not own:

- cabinet product destinations;
- sidebar active state;
- meetings/settings product navigation.
