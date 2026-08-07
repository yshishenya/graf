# Data Model: Launch Landing Redesign

This feature introduces no persistent domain entities, schema changes or lifecycle state.

The public experience consumes existing server-provided URLs and static assets:

- `download_url`: canonical route from landing CTA to `/download`.
- `start_url`: canonical route from public pages to the existing login journey.
- `public_static_asset_url`: fingerprinted URL for local landing CSS and product screenshots.
- `cabinet_static_asset_url`: fingerprinted URL for the official GRAF wordmark and favicon.

Future price/catalog data is explicitly outside this feature. When the billing slice is approved, its public catalog projection remains the sole authority for any visible amount.
