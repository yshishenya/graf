# Contract: Cabinet Shell, Components, HTMX, And WebView Boundary

## Fixed Frontend Foundation

Feature 058 implementation must use:

- Jinja templates for server-rendered pages and fragments.
- One local static `cabinet.css` file with CSS custom properties and semantic classes.
- Centralized Lucide-style inline SVG icons.
- One local vendored `htmx-2.0.10.min.js`.
- A small local `cabinet.js` only for component-owned DOM behavior that native HTML and HTMX do not cover.

Feature 058 implementation must not use:

- Tailwind or Tailwind-style utility tooling.
- Bootstrap, daisyUI, Flowbite, shadcn/ui, Web Component UI kits, or other ready UI kits.
- React, Vue, Svelte, Next.js, hydration, client-side stores, or standalone frontend app shells.
- CDN UI assets, external fonts, third-party analytics scripts, component preview apps, design-system packages, or frontend build pipelines.

## Route Matrix

| Surface | Route | Normal response | HTMX response | Notes |
|---------|-------|-----------------|---------------|-------|
| Browser | `/meetings` | Full cabinet page | List/workspace fragment only when requested by an approved target | Preserves existing URL. |
| Browser | `/meetings/{meeting_id}` | Full detail page | Detail region fragment only when requested by an approved target | Preserves existing URL. |
| Browser | `/meetings/{meeting_id}/deletion-report` | Full deletion report page | Report region fragment only when requested by an approved target | Metadata-safe copy only. |
| Desktop WebView | `/desktop/meetings` | Full embedded cabinet page | List/workspace fragment only when requested by an approved target | WebView owns online nav after migration. |
| Desktop WebView | `/desktop/meetings/{meeting_id}` | Full embedded detail page | Detail region fragment only when requested by an approved target | No native capture controls in HTML. |
| Desktop WebView | `/desktop/meetings/{meeting_id}/deletion-report` | Full embedded deletion report page | Report region fragment only when requested by an approved target | Must be allowed by exact route kind. |
| Auth | `/login`, `/sign-up`, email start/verify routes | Full auth pages or redirects | No cabinet fragment contract | Loading login does not mark cabinet ready. |

## Response Mode Rules

- Normal requests return full HTML with layout shell.
- HTMX requests return only the intended bounded region.
- Responses that vary by HTMX state set `Vary: HX-Request`.
- Auth-required, validation-error, unavailable, and problem responses are valid fragment states when the request is HTMX.
- Machine-readable JSON API endpoints under `/api/v1/cabinet/...` keep existing operation IDs and response models unless a later API-specific spec changes them.

## Component Contract

The initial cabinet catalog must cover:

- Primitive controls: button, icon button, link, input, select/filter, checkbox, chip/badge, tab, tooltip/help affordance, loader, text treatment, status label.
- Composed sections: sidebar navigation, workspace/account header, meeting row, selection toolbar, playback controls, detail side panel, confirmation dialog, status banner, empty state, unavailable state, auth form.

Each component must declare or test:

- normal, hover, focus, disabled, unavailable, loading, selected, destructive, error, empty, and overflow-text states when relevant;
- Russian labels and long-label behavior;
- accessible name requirements;
- visible focus;
- keyboard operation;
- minimum usable target size of 24 by 24 CSS pixels unless equivalent spacing is validated.

Component extension rules:

- Add a new primitive only when at least two pages or one composed section need the behavior.
- Add a new composed section when it owns a repeated cabinet workflow region, not a one-off decoration.
- Put structure in `templates/cabinet/components/*.html`, visual behavior in `static/cabinet/cabinet.css`, and bounded DOM behavior in `static/cabinet/cabinet.js`.
- Keep route handlers responsible for authorization, lifecycle, deletion, egress, and data loading; components receive already-authorized display values only.
- Add or update unit coverage for every new component state before migrating a page to it.

## Template Data Contract

Templates receive already-authorized view data only.

Templates must not:

- open database sessions;
- select tenants;
- authorize users;
- decide deletion lifecycle;
- decide egress policy;
- read local desktop paths;
- render raw private evidence.

Templates must:

- escape output by default;
- limit trusted HTML to reviewed component-owned fragments;
- keep private content out of logs, screenshots, diagnostics, and committed evidence.

## CSRF Contract

Unsafe cookie-authenticated browser/WebView actions require anti-forgery proof.

Accepted proof forms:

- hidden form field named `csrf_token`;
- request header `X-CSRF-Token` for HTMX or fetch-style requests.

Failure behavior:

- no mutation;
- bounded Russian copy;
- metadata-safe logs only;
- fragment response for HTMX requests and full-page/problem response for normal requests.

## Desktop WebView Boundary

Native macOS shell owns:

- Record/Pause/Resume/Stop;
- active capture indicator;
- permission recovery;
- local queue/upload truth;
- local diagnostics;
- route health truth;
- offline recovery.

WebView owns:

- online cabinet navigation;
- authenticated meeting list/detail;
- playback review surface;
- outcomes and metadata-safe review states;
- deletion report and bounded deletion action surfaces;
- account/workspace menu only when server/auth state is valid.

Route policy must classify exact route kinds and must not rely on broad substring matching.

## Evidence Contract

Validation evidence may include:

- route kind;
- surface mode;
- viewport size;
- component state names;
- safe counts;
- pass/fail outcome;
- safe error reason.

Validation evidence must not include:

- raw audio;
- transcript text;
- generated outcome text;
- signed URLs;
- object keys;
- credentials or tokens;
- private local paths;
- private meeting identifiers;
- real account identifiers.
