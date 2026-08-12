# Data Model: Launch Landing Redesign

This feature introduces no database entities or schema changes. It clarifies the
existing browser consent state and public-response policy.

The public experience consumes existing server-provided URLs and static assets:

- `download_url`: canonical route from landing CTA to `/download`.
- `start_url`: canonical route from public pages to the existing login journey.
- `public_static_asset_url`: fingerprinted URL for local landing CSS and product screenshots.
- `cabinet_static_asset_url`: fingerprinted URL for the official GRAF wordmark and favicon.

## Browser consent state

The existing consent record remains local to the browser and contains only:

- consent copy version and decision timestamp;
- normalized granted categories;
- derived state: all, necessary only, customized or revoked;
- the allowlisted public page path.

The record contains no account identifier, meeting content, raw URL, query,
hash, title or free-form referrer. `analytics`, `advertising_attribution` and
`behavior_replay` remain independent optional categories. Revocation disables
the active provider for the current page; a replay-category change requires a
reload because Webvisor is fixed at counter initialization.

## Public response policy

- HTML responses receive one shared set of public security headers.
- Fingerprinted `?v=` public static assets may be cached immutable for one year.
- Unversioned public assets stay revalidated so installer URLs and stable asset
  paths cannot become permanently stale.

Future price/catalog data is explicitly outside this feature. When the billing slice is approved, its public catalog projection remains the sole authority for any visible amount.
