# Data Model: Production Landing Refresh

## PublicOfferView

Server-rendered, read-only value derived from two effective `BillingPlanVersion` rows.

- `plan_code`: `personal`
- `monthly_amount_minor`: integer, exactly `100000` for this release
- `annual_amount_minor`: integer, exactly `1000000` for this release
- `currency`: `RUB`
- `monthly_label`: localized display string
- `annual_label`: localized display string
- `annual_saving_minor`: `monthly_amount_minor * 12 - annual_amount_minor`
- `annual_saving_label`: localized exact saving
- `trial_days`: `7`
- `offer_version`: non-empty version shared with checkout acceptance
- `catalog_ready`: true only when both rows are enabled, effective and valid
- `catalog_ready`: true only when the exact approved monthly and annual rows are current and mutually consistent; this controls publication of the tariff
- `checkout_enabled`: current runtime checkout flag
- `sale_ready`: true only when `catalog_ready` is true, checkout settings are valid and the current environment/shop has a complete active set of required `billing_launch_gates`; this controls any promise of immediate payment

Validation rules:

- Month and year rows use the same plan, currency, storage, processing mode and offer version.
- Amounts match the release-approved prices.
- The landing does not infer readiness from template constants.
- A missing, stale, disabled or mismatched row produces a fail-closed public state.
- Launch-gate readiness is evaluated for the exact environment and payment shop used by checkout; a gate for another environment, shop or expired approval never enables public sale truth.

## PublicAnalyticsEvent

- `event_name`: one of the nine contract names
- `page_path`: `/` or `/download`; never includes query/hash
- `surface`: `public_landing` or `public_download`
- `section_id`: optional allowlisted section
- `cta_location`: optional allowlisted CTA location
- `target_kind`: optional allowlisted destination kind
- `product_tab`: optional `recording|transcript|outcomes`
- `pricing_cycle`: optional `month|year`
- `faq_item`: optional stable FAQ identifier
- `campaign_attribution`: safe normalized UTM subset only

Forbidden fields include visitor/account IDs, email, phone, field contents, payment data, meeting identifiers, transcript/audio/outcome content, full referrer URLs, full location URLs, query and hash.

## DownloadOption

- `platform`: `macos|windows|linux`
- `status`: `available|planned`
- `minimum_version`: `14.5` for macOS only
- `architectures`: `Apple Silicon and Intel` for macOS only
- `artifact_url`: present only for macOS and points to fingerprinted `downloads/graf.pkg`
- `analytics_location`: `download_page_installer` for the available artifact

Only `available` options can render an anchor. Windows and Linux never receive package URLs in this release.

## PublicProductTab

- `id`: `recording|transcript|outcomes`
- `label`: localized visible label
- `panel_id`: unique ARIA panel target
- `image_asset`: public-safe current product asset
- `description`: product-truth copy for the same synthetic scenario
- `active`: exactly one tab in enhanced mode; all panels remain meaningful without JavaScript
