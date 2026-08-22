# Research: Production Landing Refresh

## Decision 1: Integrate into the existing public module

**Decision**: Port the approved local HTML/CSS into the current FastAPI/Jinja templates and public static bundle.

**Rationale**: The product already owns `/`, `/download`, legal pages, canonical metadata, fingerprinted assets, CSP headers and the installer mount. Reusing that boundary preserves authentication, deployment and rollback behavior.

**Alternatives considered**: A separate static host or copying `index.html` directly to Nginx was rejected because it would duplicate routes, legal links, analytics configuration and asset versioning.

## Decision 2: Keep `/download` as a distinct styled page

**Decision**: Retain the existing `/download` route and one universal `graf.pkg` link, while restyling it to match the new landing. Windows and Linux remain visibly planned and non-clickable.

**Rationale**: The route and runtime mount are already tested and point to the current Developer ID/notarized universal package. The landing CTAs can stay stable while the binary changes independently.

**Alternatives considered**: A direct hero link to the package was rejected because it removes platform/context guidance and makes goal attribution and future platform additions brittle.

## Decision 3: Derive public paid truth from the approved catalog

**Decision**: Set the product prices to 100,000 and 1,000,000 minor RUB units and render the public tariff from an effective month/year catalog that matches the offer version. Keep immediate-payment copy and actions behind the stronger checkout and launch-gate state. Missing or disabled catalog stays fail-closed for the tariff itself.

**Rationale**: Production currently has no catalog rows and checkout is disabled. The current repository explicitly makes `billing_plan_versions` the payment authority. Publishing the approved tariff and accepting money are separate states: a hard-coded landing-only number would drift, while opening payment without provider proof would be unsafe.

**Alternatives considered**: Always rendering template constants was rejected due to drift. Hiding an approved catalog tariff until checkout opens was rejected by the owner because the price must be published immediately. Enabling checkout as part of a visual deploy was rejected because production has no active billing launch-gate rows and the runbook requires test-shop, controlled canary and independent approvals.

## Decision 4: Express annual value truthfully

**Decision**: Show `10,000 RUB/year` and `2,000 RUB saved per year`, not `-20%`.

**Rationale**: Twelve monthly payments cost 12,000 RUB; a 10,000 RUB year is a 16.67% reduction. `-20%` would be mathematically false.

**Alternatives considered**: Rounding to `-17%` is accurate enough but less stable than the exact 2,000 RUB saving. `Two months free` is also true but was previously removed by the owner.

## Decision 5: Use verified product assets in the approved composition

**Decision**: Keep the three-tab layout but publish only current interface captures or deterministic public-safe derivatives. Reuse the verified transcript/outcome assets and create any recording asset from the actual current UI.

**Rationale**: This preserves the intended visual proof without leaking project data or presenting a fictional product screen.

**Alternatives considered**: User-provided raw screenshots and fully generative UI images were rejected for privacy and product-truth risk.

## Decision 6: Limit immediate Yandex Metrica to explicit public events

**Decision**: Load the Yandex tag immediately on `/` and `/download` only, with Webvisor, click maps, form analytics, advanced matching and automatic outbound-link tracking disabled. Send an explicit safe path hit and allowlisted goals.

**Rationale**: The owner selected immediate pre-consent loading. The narrow configuration reduces data collection and keeps query/hash, account fields and meeting content out of the provider payload.

**Alternatives considered**: Consent-gated Metrica is technically safer but was not selected. Yandex's official opt-out switch disables both cookies and collection, so there is no supported client-side mode that collects normal visits without cookies. Server-side Measurement Protocol was rejected as a replacement because it still requires an identifier and Yandex documents it as a complement to the web tag.

## Decision 7: Preserve goal names where possible

**Decision**: Keep the six existing public goal names for historical continuity and add three new goals for product tabs, pricing-cycle selection and FAQ openings.

**Rationale**: Reusing stable events protects existing dashboards while adapting the funnel to the new interaction model.

**Alternatives considered**: Renaming every goal was rejected because it destroys historical comparability without adding business value.

## Decision 8: Treat external Metrica and billing activation as operational gates

**Decision**: Code and tests may be completed locally, but production activation requires authenticated counter access and legal approval for immediate Metrica. Checkout additionally requires effective catalog rows, provider canary and all existing billing launch approvals.

**Rationale**: The production runtime has a public counter configured but public analytics disabled; it has no product-counter OAuth path. Billing has no catalog or active launch gates. These cannot be fabricated in source control.

**Alternatives considered**: Silent runtime mutation or inventing approval receipts was rejected because both would bypass explicit product safety controls.
