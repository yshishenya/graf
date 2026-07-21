# Feature Specification: Public Landing Analytics

**Feature Branch**: `codex/093-public-landing-analytics`

**Created**: 2026-07-08

**Status**: Implemented, released, and live on the public production scope; campaign launch remains gated

**Input**: User direction: add very detailed product analytics to the public
landing and advertising conversion path. The first implementation should use
ready-made analytics products, with Yandex Metrica as the Phase 1 analytics
provider for the Russia-first landing funnel. GA4, Google Ads tags, and other
Google analytics products are explicitly deferred until a later legal-approved
slice. PostHog/product activation analytics is planned as Phase 2 after the
landing/download funnel is safe and measurable.

## Clarifications

### Session 2026-07-08

- Lane: high-risk product/privacy/egress area. The slice adds third-party
  public analytics, advertising attribution, consent behavior, session
  observation, and release/campaign readiness gates.
- Phase 1 scope is Yandex Metrica, Yandex Direct attribution readiness, Yandex
  Webvisor/behavior tooling, and self-hosted CookieConsent v3.1.0 on `/` and
  `/download` only. GA4, Google Analytics, Google Ads tags, Google Tag Manager,
  PostHog, and product activation analytics are out of Phase 1.
- Phase 1 must not add custom analytics storage, home-grown heatmaps, custom
  replay, or a product-event pipeline. Use ready-made provider capabilities.
- The primary web conversion is installer download intent from `/download`.
  Landing CTA clicks, download page views, and login intent are secondary
  conversion steps. Product activation must not be claimed until Phase 2 is
  implemented.
- Consent defaults are privacy-first: analytics disabled when not configured;
  no non-essential analytics identifiers, advertising storage, or replay until
  consent permits it; necessary-only, non-granted category, or revoked consent
  stops future non-essential event emission.
- Consent UX must avoid repeated interruptions: one non-blocking Russian
  consent control with `accept all`, `necessary only`, and `customize` choices,
  persisted per consent-copy version, plus a public footer/settings entry to
  change the choice later.
- Consent categories are `necessary` (always on), `analytics`, `advertising
  attribution`, and `behavior replay`. `Accept all` enables maximum Phase 1
  measurement; `necessary only` loads no analytics; `customize` applies the
  selected optional categories.
- CookieConsent v3.1.0 is a pinned local static asset with MIT attribution.
  Public pages must not load CookieConsent from a CDN or other third-party
  runtime host.
- Session replay/behavior recording is allowed only for public landing and
  download pages after consent. It is forbidden on login, authenticated
  cabinet, meeting, upload, playback, deletion, admin, desktop embedded, and
  other content-bearing surfaces.
- Legal/compliance pages for privacy, cookies, terms, and analytics consent
  are required before campaign launch. Landing-page cookie/analytics consent is
  separate from account/product Terms acceptance, which belongs to
  registration, login, installer, or first app use.
- Yandex counter ID and ad account settings are runtime configuration and
  external dashboard setup, not committed repository data. Validation evidence
  remains metadata-only.
- Q: Should Phase 1 implement Google/GA4 or Google Ads tracking? -> A: No.
  Phase 1 excludes Google completely; Google can return only in a later
  legal-approved feature slice with updated privacy, cross-border, and consent
  evidence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Where Visitors Come From (Priority: P1)

A product/growth owner can open analytics reports and understand how many
visitors came to the public landing, which campaign/source/medium brought them,
and which traffic moved toward download.

**Why this priority**: The first business question is whether paid and organic
traffic produces qualified landing visits and download intent. Without reliable
source and campaign attribution, ad spend cannot be optimized.

**Independent Test**: Visit the public landing with representative UTM-tagged
URLs for at least two campaign sources, grant analytics consent, click toward
download, and confirm the visit/source/campaign and conversion appear in the
approved analytics dashboards without private user or meeting data.

**Acceptance Scenarios**:

1. **Given** a visitor opens `/` from a tagged campaign URL, **When** analytics
   consent permits measurement, **Then** the approved reports show the visit by
   source, medium, campaign, content, term, landing page, device class, and
   geography at an aggregate level.
2. **Given** a visitor opens `/` without campaign tags, **When** analytics
   consent permits measurement, **Then** the approved reports classify the
   visit as direct, organic, referral, or unknown without inventing campaign
   values.
3. **Given** a visitor clicks from `/` to `/download`, **When** analytics
   consent permits measurement, **Then** the funnel shows landing-to-download
   progression under the same source/campaign where the provider can preserve
   attribution.
4. **Given** a visitor chooses necessary-only consent, **When** they use the
   landing and download pages, **Then** non-essential analytics identifiers,
   session replay, and advertising cookies remain disabled and the limitation
   is reflected in measurement caveats rather than hidden.

---

### User Story 2 - Understand Landing Behavior And Conversion (Priority: P1)

A product owner can see how visitors move through the landing page: which CTA
they click, how far they scroll, whether they reach the download page, and
whether they click the installer download action.

**Why this priority**: The existing public landing is an install-first flow.
Optimization needs a page-behavior view before copy, layout, or paid campaign
changes are judged.

**Independent Test**: Complete representative paths from first viewport,
mid-page, final CTA, header download, login link, and direct `/download`
entry; confirm each path is measured as a named conversion step in the approved
analytics products.

**Acceptance Scenarios**:

1. **Given** a consenting visitor views the first screen, **When** they click
   the hero download CTA, **Then** the CTA click is counted with a stable
   location label and contributes to the landing CTA conversion metric.
2. **Given** a consenting visitor scrolls through major sections, **When** they
   reach benefit, outcome, trust, and final CTA sections, **Then** section
   visibility is measurable without sending visible text, transcript-like
   examples, or private content.
3. **Given** a consenting visitor reaches `/download`, **When** they click the
   installer download link, **Then** installer download intent is counted as the
   primary web conversion.
4. **Given** a visitor enters directly on `/download`, **When** they click the
   installer download link, **Then** the conversion is attributed to the direct
   download landing path, not falsely to the main landing CTA.
5. **Given** a user clicks `Войти` instead of download, **When** the link
   opens `/login?next=/meetings`, **Then** the login intent is measured as a
   secondary path and not merged with installer download intent.

---

### User Story 3 - Keep Analytics Privacy-Safe And Consentful (Priority: P1)

A privacy/product owner can prove that public analytics does not capture
meeting content, credentials, account identifiers, private file paths, raw
transcripts, audio data, or cabinet/meeting behavior outside the approved
public scope.

**Why this priority**: Analytics introduces third-party egress and session
observation. It must not weaken GRAF's data-boundary promise or the existing
metadata-only evidence policy.

**Independent Test**: Inspect the public landing and download pages in
disabled, consent unknown, accept-all, necessary-only, customized, and revoked
states; confirm that only approved metadata-only events and provider calls
occur and that session replay is limited to approved public surfaces.

**Acceptance Scenarios**:

1. **Given** analytics IDs are not configured or analytics is disabled, **When**
   a visitor opens `/` or `/download`, **Then** no third-party analytics script
   or tracking request is loaded.
2. **Given** a visitor has not granted analytics consent, **When** the public
   page loads, **Then** analytics providers do not load and no session replay
   or non-essential cookie storage is active.
3. **Given** a visitor grants the analytics category, **When** analytics begins,
   **Then** only approved public page, source, device, section, CTA, and
   download-intent metadata is sent.
4. **Given** a visitor chooses necessary-only consent or later revokes
   analytics consent, **When** they continue using public pages, **Then**
   non-essential analytics stops, replay remains off, and future page
   interactions are not sent as identified events.
5. **Given** a user reaches `/login`, authenticated cabinet pages, meeting
   review, upload, playback, deletion, admin, or desktop embedded pages,
   **When** this feature is the only analytics slice deployed, **Then** session
   replay and landing analytics instrumentation do not observe those surfaces.

---

### User Story 4 - Prepare Product Activation Attribution (Priority: P2)

A product owner has a clear Phase 2 measurement contract that can later connect
campaigns to real activation, such as app first open, account connection,
autorecord enablement, first completed recording, and first result viewed.

**Why this priority**: Web download intent is useful but incomplete. The
business ultimately needs to know which campaigns create activated users and
valuable first outcomes.

**Independent Test**: Review the Phase 2 event contract and confirm that the
first landing release does not implement product/session tracking beyond public
pages, while future product analytics can connect activation using safe,
hashed, consent-respecting identifiers.

**Acceptance Scenarios**:

1. **Given** the Phase 1 landing analytics is implemented, **When** a report is
   reviewed, **Then** it clearly separates web conversion from product
   activation and does not claim campaign-level activation attribution yet.
2. **Given** Phase 2 is planned, **When** product activation events are listed,
   **Then** each event has a safe name, safe fields, owner, consent/notice
   requirement, and forbidden-data list.
3. **Given** future activation analytics needs user continuity, **When** an
   identity strategy is proposed, **Then** it uses a safe hashed or provider
   pseudonymous identifier and never sends email, account name, meeting title,
   transcript, raw audio, local path, token, or signed URL.
4. **Given** product activation analytics is not yet deployed, **When** a paid
   campaign is optimized, **Then** the owner uses installer download as the
   primary web conversion and records that deeper activation attribution is
   pending Phase 2.

---

### User Story 5 - Operate And Validate Analytics Reliably (Priority: P2)

An operator can enable, disable, and validate analytics safely across local,
test, staging, and production environments without breaking the public landing
or silently losing conversion events.

**Why this priority**: Analytics is operationally fragile. Missing IDs,
blocked scripts, consent misconfiguration, duplicate events, or ad-platform
drift can make paid acquisition decisions wrong.

**Independent Test**: Run configured and unconfigured environments,
accept-all, necessary-only, customized, revoked, duplicate navigation, and
blocked-provider simulations; the landing remains usable and validation
evidence identifies expected analytics state without secrets or private
payloads.

**Acceptance Scenarios**:

1. **Given** analytics is disabled by environment or missing required IDs,
   **When** public pages render, **Then** the pages remain fully usable and no
   broken script URLs, console-critical errors, or empty provider calls appear.
2. **Given** analytics is enabled with approved IDs, **When** public pages
   render, **Then** exactly one approved instance per provider is initialized
   and duplicate page or CTA events are not emitted from one user action.
3. **Given** an analytics provider is blocked by a browser extension, privacy
   tool, network policy, or provider outage, **When** the visitor uses the
   public pages, **Then** the user experience still works and the known
   measurement gap is documented.
4. **Given** a release or campaign launch is prepared, **When** validation is
   run, **Then** a metadata-only evidence checklist proves provider setup,
   consent behavior, conversion events, UTM attribution, replay scope, and
   dashboard readiness.

### Edge Cases

- A campaign link has missing, malformed, mixed-case, duplicated, or
  personally identifying UTM parameters.
- A visitor enters on `/download` directly, reloads, opens multiple tabs, uses
  private browsing, blocks cookies, blocks analytics scripts, or changes
  consent mid-session.
- A visitor grants consent after the first page has already loaded.
- A visitor chooses necessary-only consent and later revokes or grants optional
  categories in a later session.
- The browser disables third-party cookies or provider storage.
- Provider scripts are slow, unavailable, blocked, or return an error.
- Bot, preview, uptime-check, or crawler traffic opens public pages.
- A visitor clicks the same CTA repeatedly or downloads the installer multiple
  times in one session.
- A new landing section or CTA is added without a stable measurement label.
- The installer asset URL changes while campaign links are active.
- The public landing is served in local/test/staging environments where real
  production analytics must not fire.
- Session replay accidentally becomes active on `/login`, cabinet, meeting
  detail, upload, playback, deletion, admin, or embedded desktop surfaces.
- Analytics events, UTM tags, or debug logs include email, phone, person name,
  company name, account identifier, private calendar/event text, meeting title,
  transcript, audio, local path, object key, token, signed URL, or passcode.
- Advertising dashboards disagree with analytics reports because of consent,
  attribution windows, blocked tags, ad-platform import delays, or duplicate
  conversion configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The first release MUST instrument only the public landing `/` and
  public download `/download` surfaces; `/login`, authenticated cabinet,
  meeting review, upload, playback, deletion, admin, and embedded desktop
  product surfaces are out of Phase 1 tracking except for ordinary navigation
  away from public pages.
- **FR-002**: The first release MUST use approved ready-made analytics products
  for public web analytics: Yandex Metrica for visits, sources, goals,
  behavior tools, and Yandex Direct readiness, plus self-hosted CookieConsent
  v3.1.0 for public-page consent. Custom analytics storage, home-grown
  heatmap/replay, GA4, Google Analytics, Google Ads tags, Google Tag Manager,
  paid CMP, or a new product-event pipeline MUST NOT be built in Phase 1.
- **FR-003**: PostHog/product activation analytics MUST be treated as Phase 2.
  Phase 1 may define the Phase 2 contract, but MUST NOT add PostHog or product
  activation tracking code.
- **FR-004**: Analytics MUST be disabled by default when the feature flag is
  off, the Yandex Metrica counter ID is absent, the environment is not
  production-like, or validation explicitly requests a no-analytics mode.
- **FR-005**: Public pages MUST render without third-party analytics scripts,
  provider requests, non-essential analytics storage, or provider cookies when
  analytics is disabled.
- **FR-006**: The public pages MUST present a clear, non-blocking Russian
  analytics/cookie consent notice before non-essential analytics storage,
  advertising identifiers, or session replay are enabled.
- **FR-007**: Consent controls MUST support `accept all`, `necessary only`,
  `customize`, persistence across public-page visits, category-level choices,
  and a way to change the choice later from public pages.
- **FR-008**: Before consent is granted, Yandex Metrica, Yandex Webvisor,
  advertising attribution tags, and any non-essential analytics provider calls
  MUST NOT load or send provider pings. Provider-supported pre-consent or
  consent-denied measurement MUST NOT be used in Phase 1.
- **FR-009**: If consent is necessary-only, revoked, or customized without the
  relevant optional category, public pages MUST stop sending non-essential
  analytics events from future interactions for that category and MUST keep
  replay inactive unless `behavior_replay` is granted.
- **FR-010**: Session replay/behavior recording MUST be limited to `/` and
  `/download`, MUST require analytics consent, and MUST be disabled on login,
  authenticated cabinet, meeting, upload, playback, deletion, admin, desktop
  embedded, and any content-bearing surface.
- **FR-011**: The implementation MUST expose stable public event names for
  `public_landing_viewed`, `public_landing_section_seen`,
  `public_landing_cta_clicked`, `public_download_viewed`,
  `public_installer_download_clicked`, and `public_login_intent_clicked`.
- **FR-012**: Event fields MUST use safe bounded labels only: page path,
  surface, section ID, CTA location, target kind, source/medium/campaign
  fields, device class, consent state, and provider-safe anonymous/session
  context where allowed.
- **FR-013**: Event fields, UTM values copied into events, logs, diagnostics,
  tests, screenshots, and evidence MUST NOT include email, phone, person name,
  company name, account identifier, private calendar/event text, meeting title,
  transcript, raw audio, local path, object key, token, signed URL, password,
  passcode, or private meeting content.
- **FR-014**: UTM handling MUST preserve standard campaign parameters:
  `utm_source`, `utm_medium`, `utm_campaign`, `utm_id`, `utm_content`, and
  `utm_term`, while normalizing reporting labels enough to avoid duplicate
  campaign rows caused only by case or whitespace differences.
- **FR-015**: UTM governance MUST define approved source, medium, campaign,
  content, and term naming rules before paid campaigns are launched.
- **FR-016**: The primary web conversion MUST be installer download intent from
  `/download`. Landing CTA click and `/download` page view MUST be secondary
  conversion steps. Login intent MUST remain a separate secondary path.
- **FR-017**: The approved analytics dashboards MUST include a funnel for
  landing view, qualified engagement or section reach, CTA click, download
  page view, and installer download click.
- **FR-018**: The approved analytics dashboards MUST support breakdown by
  source, medium, campaign, content/creative, term, landing path, device class,
  country/region, consent/grantable population where available, and date.
- **FR-019**: The feature MUST document dashboard interpretation caveats for
  consent rejection, blocked providers, bot/crawler traffic, direct traffic,
  attribution windows, ad-platform import delays, duplicate clicks, and
  installer downloads that do not prove product activation.
- **FR-020**: The feature MUST provide a validation checklist for configuring
  Yandex Metrica goals, Webvisor/behavior tools, and Yandex Direct conversion
  readiness without committing live provider IDs, account IDs, credentials, or
  secrets.
- **FR-021**: The landing/downloading user experience MUST remain usable if
  analytics scripts fail, are blocked, load slowly, or are disabled.
- **FR-022**: Analytics MUST NOT alter public landing copy, CTA destinations,
  download destination, local asset rendering, accessibility entry points, or
  install-first conversion path except for the consent control and approved
  analytics-related metadata.
- **FR-023**: Local, test, and CI validation MUST prove both no-analytics and
  enabled-analytics rendering states without contacting live analytics
  providers unless explicitly running a production smoke.
- **FR-024**: Production validation MUST use metadata-only evidence and MUST
  not store real visitor identifiers, raw cookies, live account IDs, or raw
  network payloads in committed files.
- **FR-025**: Phase 2 planning MUST define the activation funnel events
  `desktop_first_opened`, `desktop_account_connected`,
  `desktop_autorecord_enabled`, `first_recording_completed`,
  `first_result_viewed`, and `first_value_session_completed` before any
  product analytics implementation begins.
- **FR-026**: Phase 2 planning MUST define a safe identity and consent strategy
  before linking campaign acquisition to authenticated or desktop product
  behavior.
- **FR-027**: Reports and product copy MUST distinguish "installer download
  intent" from "installed", "signed in", "recording enabled", "first meeting
  completed", and "first result viewed".
- **FR-028**: The feature MUST update release/campaign readiness guidance so
  campaign launch is blocked until conversion events, consent behavior, replay
  scope, and dashboard access are validated.
- **FR-029**: The public site MUST expose links from the consent UI and footer
  to privacy policy, cookie policy, terms, analytics-consent text, and cookie
  settings before paid campaign launch.
- **FR-030**: Public cookie/analytics consent MUST NOT be treated as acceptance
  of product Terms. Terms acceptance for account, installer, desktop app,
  recording, or transcription behavior MUST be handled in the relevant product
  flow or later feature slice.
- **FR-031**: The Phase 1 legal readiness checklist MUST include Russian
  privacy/cookie/analytics-consent text review, personal-data operator notice
  review, and a rule that foreign analytics providers require separate
  cross-border and consent approval before being enabled.
- **FR-032**: CookieConsent assets MUST be self-hosted from pinned v3.1.0 local
  static files with MIT attribution. Public pages MUST NOT render CookieConsent
  CDN URLs or any third-party consent-manager runtime URL.

### Key Entities *(include if feature involves data)*

- **PublicAnalyticsConsent**: A visitor's public-page analytics choice. Key
  attributes: state (`unknown`, `accepted_all`, `necessary_only`,
  `customized`, `revoked`), optional category grants (`analytics`,
  `advertising_attribution`, `behavior_replay`), decision time, public surface
  where the decision occurred, and version of the consent copy. It must not
  contain real user identity or meeting data.
- **PublicCampaignAttribution**: Safe campaign metadata attached to public page
  visits and conversion events. Key attributes: source, medium, campaign,
  campaign ID, content/creative, term, landing path, referrer category, and
  normalization status.
- **PublicLandingEvent**: A metadata-only event describing a public-page action
  or milestone. Key attributes: event name, page path, section ID, CTA
  location, target kind, consent state, campaign attribution, device class,
  and provider delivery status.
- **PublicConversionGoal**: A named conversion step used in analytics
  dashboards. Key attributes: goal name, funnel order, primary/secondary
  classification, counted event, allowed surfaces, deduplication rule, and
  dashboard owner.
- **AnalyticsProviderConfiguration**: Non-secret runtime configuration that
  determines whether Yandex Metrica and consent-gated behavior tooling are
  enabled. Key attributes: provider enabled state, configured ID presence,
  environment eligibility, replay allowed state, and validation mode. Live IDs
  are configuration values, not committed spec data.
- **Phase2ActivationEventContract**: Future product analytics contract for
  activation events beyond public pages. Key attributes: event name, product
  surface, safe fields, consent/notice requirement, identity linkage rule,
  forbidden data, owner, and validation requirement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a controlled production-like validation with tagged campaign
  URLs, a product owner can see landing visits and installer download clicks by
  source, medium, campaign, content, and term in the approved analytics reports
  within Yandex Metrica's normal reporting delay.
- **SC-002**: 100% of public-page analytics events emitted during validation
  use the approved event names and safe field set, with zero forbidden private
  or content-bearing values found by inspection and automated scans.
- **SC-003**: Consent validation proves public-page states for analytics
  disabled, consent unknown, accept all, necessary only, customized category
  choices, and revoked consent.
- **SC-004**: With consent necessary-only, revoked, or analytics disabled,
  validation observes zero non-essential analytics script loads, replay
  sessions, provider cookies, or custom conversion events from future
  public-page interactions.
- **SC-005**: With analytics enabled and the analytics category granted, one
  visitor action produces no more than one event per provider for each named
  conversion step.
- **SC-006**: Session replay or behavior recording is observable only on `/`
  and `/download` when `behavior_replay` consent is granted, and is absent
  from login, cabinet, meeting, upload, playback, deletion, admin, and embedded
  desktop surfaces.
- **SC-007**: Public-page UX validation confirms the landing and download pages
  remain usable when provider scripts are blocked or slow.
- **SC-008**: A campaign launch checklist lets a non-engineer verify, in under
  30 minutes, whether source attribution, primary conversion, secondary
  conversion steps, consent behavior, legal-page links, legal-readiness
  evidence, and replay scope are ready for paid traffic.
- **SC-009**: The first release explicitly labels installer download as web
  conversion only and does not claim product activation attribution until the
  Phase 2 activation contract is implemented and validated.
- **SC-010**: The Phase 2 activation contract covers all first-value milestones
  from app first open through first result viewed, including safe identity,
  consent/notice, forbidden data, and validation requirements for every event.

## Assumptions

- The public landing remains an install-first flow:
  `landing -> download -> installer -> login/cabinet -> first use`.
- The primary paid acquisition channel for Phase 1 is Yandex. Google campaign
  analytics is deferred until a separate legal-approved slice.
- The first implementation will not add a tag manager in Phase 1.
- The first implementation will not add PostHog, Amplitude, Mixpanel, Clarity,
  Matomo, or a custom product-event store.
- Yandex Webvisor/behavior recording is useful for public landing diagnosis,
  but must be consent-gated and scoped to public pages only.
- Yandex Metrica goals are needed for Yandex Direct optimization. GA4 key
  events and Google Ads conversion import are not part of Phase 1.
- Consent and analytics copy will be in Russian and will avoid legal
  overpromises.
- Live analytics provider IDs, ad account IDs, conversion IDs, credentials,
  cookies, and visitor identifiers are not committed to the repository.
- Existing server-rendered public templates and static assets remain the
  implementation surface for Phase 1.
- Production deploy and paid campaign launch are separate release-lane
  decisions. The implementation is live on the approved public scope, while
  campaign launch remains blocked until the legal, consent, conversion, and
  provider-readiness gates are approved.
