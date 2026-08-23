# Contract: Yandex Metrica Goals

## Provider boundary

- Allowed surfaces: `/` and `/download` only.
- Initialization: immediate when public analytics runtime is enabled.
- Explicit hit path: `/` or `/download`; never `window.location.href`.
- Disabled: Webvisor, click map, scroll map, form analytics, advanced matching and automatic outbound-link tracking.
- Counter ID remains runtime configuration.

## Goals

| Goal/event name | Trigger | Allowed labels |
|---|---|---|
| `public_landing_viewed` | One initial safe hit on `/` | path, surface, safe campaign attribution |
| `public_landing_section_seen` | First 52% visibility of an allowlisted section | section ID, path, surface |
| `public_landing_cta_clicked` | Download-page CTA on `/` | CTA location, target kind |
| `public_download_viewed` | One initial safe hit on `/download` | path, surface, safe campaign attribution |
| `public_installer_download_clicked` | Universal package link | CTA location, target kind |
| `public_login_intent_clicked` | Login link on either public page | CTA location, target kind |
| `public_product_tab_selected` | User selects a different product tab | product tab |
| `public_pricing_cycle_selected` | User switches month/year | pricing cycle |
| `public_faq_opened` | User opens a FAQ item | FAQ item ID |

Each event is deduplicated per page/action key. Default tab, default pricing and closed FAQ state do not send interaction goals.

## Stable labels

- Sections: `hero`, `audience`, `workflow`, `pricing`, `faq`, `final_cta`
- CTA locations: `header_download`, `hero_download`, `pricing_download`, `final_download`, `header_login`, `final_login`, `download_page_installer`, `download_page_login`
- Target kinds: `download_page`, `installer_package`, `login`
- Product tabs: `recording`, `transcript`, `outcomes`
- Pricing cycles: `month`, `year`
- FAQ IDs: stable semantic identifiers, never question text

## Verification

1. Intercept `window.ym` and assert one `init` call.
2. Assert all forbidden collection features are false.
3. Exercise every action and compare ordered `reachGoal` calls to this table.
4. Repeat actions and prove required deduplication.
5. Open query/hash/private-looking URLs and prove only safe normalized values leave.
6. Verify no Yandex script/config on legal, auth, cabinet, admin or meeting surfaces.
7. In the Yandex account, replace the landing goals with these exact names and verify a synthetic public session.
