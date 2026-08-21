# Security and privacy validation

- Public assets are local and fingerprinted; no CDN, remote font or frontend framework was introduced.
- Screenshots contain synthetic text and no metadata chunks.
- Secret-pattern scan over public templates, scripts, styles and screenshot assets found no credential.
- Public analytics stays limited to `/` and `/download`; legal, authentication, cabinet, admin and meeting surfaces do not receive the public counter configuration.
- Public Yandex settings explicitly disable Webvisor, click maps, automatic link tracking and automatic bounce tracking.
- Event payloads use server-owned allowlists for page, section, CTA, tab, pricing cycle and FAQ labels; raw URL, title, email, transcript, payment data and form values are excluded.
- Missing or unavailable billing catalog data leaves the landing available but hides paid-sale copy.
- Shared private product analytics functions remain present and are covered by preservation tests.
- Security header, canonical, sitemap, immutable-cache and read-only installer-mount contracts pass.

No production secret, OAuth credential or provider token was written to validation evidence. The public Yandex counter identifier and provider domain are intentionally recorded only in the provider-side validation evidence needed to reproduce the configured goals.
