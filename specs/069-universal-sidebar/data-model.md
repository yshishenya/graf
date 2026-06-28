# Data Model: Universal Cabinet Sidebar

## Cabinet Navigation Item

Represents one destination in the primary cabinet sidebar.

Fields:

- `id`: stable destination identifier used for active state.
- `label`: visible destination text.
- `href`: destination URL for the current surface mode.
- `icon`: visual icon identifier from the existing cabinet icon set.
- `enabled`: whether the destination is currently available.
- `count`: optional numeric badge for pending user action.

Rules:

- `id` is stable across browser and desktop embedded surfaces.
- `href` may differ between browser and desktop embedded surfaces.
- Disabled items remain visible only as future/unavailable destinations and are not keyboard-focusable.
- Exactly one enabled item exposes the current destination programmatically and visually.
- Disabled items never expose current destination state.

## Cabinet Navigation Model

Represents the sidebar data for a full cabinet page.

Fields:

- `active`: active destination id.
- `items`: ordered `Cabinet Navigation Item` collection.
- `workspace_title`: fallback text title for the workspace/brand region.
- `workspace_subtitle`: optional supporting text for the workspace/brand region.

Rules:

- Defaults to the meetings destination when no active destination is specified.
- Resolves to exactly one current enabled destination for every covered full page.
- Browser and desktop embedded modes share the same ids, labels, availability states, icons, and counts.
- Route paths are adapted per surface mode without changing the destination identity.

## Cabinet Shell

Represents the full authenticated cabinet page layout.

Fields:

- `surface_mode`: standalone browser or desktop embedded.
- `navigation`: `Cabinet Navigation Model`.
- `content_region`: one page-owned content region.
- `sidebar_brand`: brand/workspace presentation.
- `sidebar_footer`: footer/trial/status presentation.

Rules:

- Full cabinet pages render exactly one shell and exactly one primary sidebar.
- Desktop embedded mode preserves compact rail behavior and accessible expand/collapse.
- Admin and auth pages are not Cabinet Shell consumers for this feature.

## Cabinet Content Fragment

Represents a partial update response.

Fields:

- `fragment_id`: stable content region identifier.
- `content`: page-owned fragment HTML.

Rules:

- Fragments never include the full shell.
- Fragments never include the primary sidebar.
- Dynamic updates target or select the intended content region and preserve the existing shell.

## State Transitions

- Browser page load -> full Cabinet Shell with browser routes.
- Desktop embedded page load -> full Cabinet Shell with embedded routes and compact-capable sidebar.
- Dynamic content update -> Cabinet Content Fragment replaces content region only.
- Active destination change -> full page renders same sidebar contract with a new active id.
