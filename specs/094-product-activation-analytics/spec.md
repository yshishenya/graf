# Feature Specification: Product Activation Analytics

**Feature Branch**: `094-product-activation-analytics`

**Created**: 2026-07-08

**Status**: Draft backlog feature for future SDD/Spec Kit discovery

**Input**: User description: "Зафиксировать отдельную будущую фичу для продуктовой аналитики приложения GRAF. Передать весь контекст из `093-public-landing-analytics`, где публичная аналитика уже ограничена `/` и `/download`, а приложение/кабинет/встречи специально не трекаются. Нужна SDD-проработка before implementation: provider, identity, consent/notice, retention/deletion truth, forbidden fields, dashboards, legal readiness, rollout gates."

## Clarifications

### Session 2026-07-08

- Q: Should B2B/workspace users have a different product telemetry consent path
  from B2C users? -> A: No. B2B/workspace and B2C users must use the same
  product telemetry gate.
- Q: Can product use continue if the user does not accept the required product
  analytics and legal terms? -> A: No. Future implementation should use a hard
  product-use gate: a user may not continue into the desktop app, cabinet, or
  authenticated product surfaces unless they accept the required Terms,
  Privacy/Personal Data processing documents, and mandatory product telemetry
  package.
- Q: Does "accept everything" allow hidden, unlimited, or content-bearing
  analytics? -> A: No. The mandatory package must stay bounded to the approved
  product activation analytics contract. It may include risk-accepted
  full-coverage Yandex Webvisor/session replay for approved browser-rendered
  pages only after masking and sanitization gates pass. It must not include
  unmasked product/cabinet/meeting replay, ad retargeting pixels, raw
  identities, meeting content, audio, transcripts, calendar text, local paths,
  secrets, signed URLs, or other forbidden fields. Any broader purpose requires
  a separate explicit future gate and legal review.
- Q: Can a user later disable the mandatory product analytics package while
  continuing to use the product? -> A: No. If the user withdraws the required
  consent or refuses updated mandatory terms, future product use must stop or
  be limited to account/legal/export/deletion flows. Future analytics events
  stop after withdrawal because normal product use is no longer available.
- Q: Where should the product owner see the full user journey? -> A: Future
  design should optimize for one primary analytics workspace, not routine
  manual exports or multi-tool reconciliation. PostHog self-hosted is the
  preferred primary full-funnel analytics home for approved public and product
  activation events. Yandex Metrica becomes a parallel all-web-pages
  measurement and advertising optimization surface; if needed, only a small
  approved set of activation milestones may be sent back to Yandex as offline
  conversions for ad optimization. A future PostHog-Yandex roadmap connector
  must not be a launch dependency.
- Q: Are Yandex Metrica and PostHog both used in parallel? -> A: Yes, future
  design should use a parallel analytics stack with role separation. PostHog is
  the primary end-to-end journey workspace and should receive the approved
  public acquisition events plus approved product activation events. Yandex
  Metrica should receive the maximum approved all-web-pages/ad measurement for
  approved browser-rendered pages, including traffic sources, goals,
  section/CTA/download events, safe authenticated page events, and
  Webvisor/session replay across all approved page classes after the mandatory
  replay/masking gate passes. Yandex may also receive approved product
  activation milestones as offline conversions for Yandex Direct optimization.
  This does not mean duplicating unlimited product detail into Yandex or
  enabling unmasked product replay.
- Q: Should Yandex Metrica remain limited to public pages, or be enabled on all
  pages? -> A: Enable Yandex Metrica on all browser-rendered web pages as a
  risk-accepted future requirement, not only `/` and `/download`. This includes
  public, download, legal, auth, cabinet, and authenticated product web
  surfaces once the future SDD approves the page inventory, legal gate, URL and
  page-title sanitization, forbidden-field controls, retention/deletion truth,
  and provider configuration. PostHog remains the primary full-funnel source of
  truth, while Yandex becomes a parallel all-web-pages measurement and
  advertising optimization surface. "All pages" does not authorize sending raw
  email, names, workspace names, meeting titles, participants, audio,
  transcripts, calendar text, object keys, signed URLs, local paths, secrets, or
  other forbidden fields to Yandex.
- Q: What is the target Webvisor/session replay coverage? -> A: Full replay
  everywhere for Yandex Webvisor/session replay is risk-accepted as the target
  for all approved browser-rendered web pages. This means public, download,
  legal, auth, cabinet, and authenticated product web surfaces should have
  Yandex replay enabled after mandatory masking-by-default, URL/title/referrer
  sanitization, form/input suppression, private DOM hiding, and QA/legal
  evidence. If a page class cannot be made safe for replay, the future SDD must
  treat that as a launch blocker or require product/route/DOM redesign rather
  than silently excluding the page. Full replay does not allow raw meeting
  content, transcript text, participant names, workspace names, emails, local
  paths, object keys, signed URLs, secrets, or other forbidden fields in replay
  payloads.
- Q: Should PostHog also include session replay for maximum daily convenience?
  -> A: Yes. PostHog Session Replay should be enabled for approved
  browser-rendered public, auth, cabinet, and product web pages so the product
  owner can move from funnels, drop-offs, cohorts, and activation events to
  matching session recordings inside the primary PostHog workspace. It must use
  the same masking-by-default, URL/title/referrer sanitization, private DOM
  hiding, input suppression, forbidden-field controls, QA evidence, and legal
  review as Yandex Webvisor. Desktop-native screen/audio replay is not
  authorized by this decision.
- Q: What is the default identity and attribution model? -> A: Use a
  server-owned attribution bridge centered on a safe `graf_attribution_id`
  and/or expiring bridge token. The bridge should connect campaign context,
  UTM/openstat values, `yclid`, Yandex ClientID when available, PostHog
  anonymous ID, public session, download click, login/signup, account
  connection, and later product activation without exposing raw email, names,
  workspace names, account IDs, user IDs, meeting IDs, device names, local
  paths, signed URLs, tokens, or content-bearing values. `desktop_first_opened`
  is always counted, but campaign-linked `desktop_first_opened` is reliable only
  when a bridge token/auth link exists; `desktop_account_connected` is the first
  reliable campaign-linked product milestone.

## SDD Carry-Forward Prompt

Use `specs/094-product-activation-analytics/sdd-prompt.md` as the prompt for
the next SDD pass. The prompt intentionally asks for discovery and decisions,
not implementation.

## Context From Feature 093

Feature `093-public-landing-analytics` completed public web analytics only:

- public surfaces: `/` and `/download`;
- provider: Yandex Metrica; safe defaults remain disabled in committed env
  templates, while approved production runtime may enable the counter through
  external environment configuration;
- no Google/GA4/GTM in Phase 1;
- no PostHog/product analytics code in Phase 1;
- consent-first public analytics with CookieConsent v3.1.0;
- Webvisor/replay only for public pages and only with `behavior_replay`
  consent;
- primary web conversion: `public_installer_download_clicked`;
- secondary web steps: landing view, section reach, CTA click, download page
  view, login intent;
- legal pages exist as draft copy; paid campaign launch remains blocked until
  legal/campaign-readiness approval, even though live Yandex counter/goals and
  provider smoke are now complete for the 093 public scope.

Post-deploy evidence from `093` that must be carried into `094`:

- the live production counter and six Yandex JS-event goals were configured for
  the public scope;
- production runtime enabled public analytics for `/` and `/download` only;
- production smoke verified container env, health endpoints, rendered HTML
  analytics config, rendered public event catalog, Yandex script reachability,
  and absence of the public analytics dispatcher on `/login`;
- a deployment bug was found and fixed where production `.env` contained the
  analytics settings but `docker-compose.yml` did not pass those runtime values
  into `rec-api`. Future analytics implementation must verify the live
  container environment and rendered pages, not only host-side `.env` files;
- live counter IDs must remain runtime/provider configuration. Do not hard-code
  live provider IDs, API keys, tokens, signed URLs, or credentials in source
  files, specs, tests, or release evidence.

Feature `093` explicitly left product activation analytics out of scope:

- no analytics in desktop app;
- no analytics in cabinet;
- no analytics on login, meeting, upload, playback, deletion, admin, API, legal,
  or desktop embedded surfaces;
- no linking anonymous public visitor data to authenticated/product behavior;
- no product replay;
- no provider SDK for product events.

Existing Phase 2 contract source:

- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`

Existing closeout evidence source:

- `specs/093-public-landing-analytics/validation/implementation-evidence.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Real Activation Funnel (Priority: P1)

A product/growth owner wants to know which acquisition sources produce real
product activation, not only installer download intent.

**Why this priority**: Public analytics can show that a visitor clicked the
installer, but it cannot show whether GRAF was opened, connected, configured,
used for a first recording, or delivered first value.

**Independent Test**: Review the approved analytics requirements and confirm
that the future funnel distinguishes public web intent from product activation
without requiring unsafe meeting, account, or content-bearing data.

**Acceptance Scenarios**:

1. **Given** a visitor came from a tagged campaign and clicked the installer,
   **When** product analytics is designed, **Then** the funnel can separate
   installer download intent from first product value.
2. **Given** a user opens the desktop app for the first time, **When** Phase 2
   analytics is approved, **Then** the event model can measure onboarding
   progress without sending local paths, device names, email, account names, or
   meeting content.
3. **Given** a user completes their first successful recording and views the
   result, **When** dashboards are reviewed, **Then** the product owner can see
   activation without exposing audio, transcript, participant, calendar, or
   meeting-title content.

---

### User Story 2 - Preserve Privacy And Consent Boundaries (Priority: P1)

A privacy/product owner wants proof that product analytics cannot silently
capture meeting content, raw identities, desktop identifiers, or cross-surface
links without an approved consent/notice and identity strategy.

**Why this priority**: Product activation surfaces are more sensitive than the
public landing because they touch desktop behavior, authentication, recording,
calendar policy, cabinet results, and meeting lifecycle.

**Independent Test**: Review the future plan and confirm it defines the
consent/legal gate, withdrawal/refusal behavior, identity linkage, forbidden
fields, deletion truth, and internal/test-user filtering before implementation
tasks exist.

**Acceptance Scenarios**:

1. **Given** no product telemetry notice or consent decision exists, **When**
   the feature is evaluated, **Then** no product analytics implementation is
   approved.
2. **Given** a proposed event field includes email, full name, workspace name,
   raw account ID, device name, local path, OAuth token, meeting title,
   transcript, audio, participant, calendar event ID, signed URL, object key, or
   passcode, **When** the event contract is reviewed, **Then** the field is
   rejected.
3. **Given** a user or workspace requests deletion, **When** product analytics
   reporting is described, **Then** the copy states what GRAF controls and what
   may remain in aggregate provider reports or exported dashboards.

---

### User Story 3 - Choose A Product Analytics Provider Safely (Priority: P1)

An operator/product owner wants a provider decision that supports funnels,
segments, retention, privacy controls, and campaign linkage without creating
unreviewed egress or compliance risk.

**Why this priority**: The provider choice affects data egress, hosting,
identity, replay, retention, deletion, dashboard access, costs, and legal
review. It cannot be hidden as an implementation detail.

**Independent Test**: Compare provider options and produce a decision record
that states whether to use self-hosted PostHog, cloud PostHog, Yandex-only
goals, another provider, or no provider until a later milestone.

**Acceptance Scenarios**:

1. **Given** PostHog is considered, **When** the decision is reviewed, **Then**
   the spec explains cloud vs self-hosted hosting, data residency, replay
   status, identity, retention, and deletion participation.
2. **Given** Yandex Metrica is considered for product analytics, **When** the
   decision is reviewed, **Then** the spec explains why it is or is not suitable
   for authenticated desktop/cabinet product activation.
3. **Given** no provider satisfies privacy and operations requirements, **When**
   the plan is reviewed, **Then** implementation remains blocked rather than
   adding custom analytics storage or an unapproved SDK.

---

### User Story 4 - Prepare Rollout And Dashboard Readiness (Priority: P2)

An operator wants product analytics to launch only after dashboards, QA,
internal filtering, legal readiness, and release gates are clear.

**Why this priority**: Product analytics can mislead campaigns if internal
traffic, test users, duplicate events, provider blockers, or partial funnels are
not handled before rollout.

**Independent Test**: Review the launch checklist and confirm it blocks rollout
until dashboard owners, event owners, validation evidence, legal status, and
campaign interpretation caveats are documented.

**Acceptance Scenarios**:

1. **Given** internal smoke users generate activation events, **When** reports
   are reviewed, **Then** internal/test traffic is excluded or clearly labeled.
2. **Given** the provider script or SDK is blocked, **When** the product still
   runs, **Then** user workflows continue and measurement loss is documented.
3. **Given** dashboards show installer download and activation side by side,
   **When** a campaign decision is made, **Then** reports clearly distinguish
   web intent from product activation and first value.

### Edge Cases

- A user downloads the installer but never opens the desktop app.
- A user opens the desktop app without coming from the public landing.
- A user installs on one device and signs in on another.
- A user has multiple workspaces or changes workspace after first login.
- A user enables auto-recording but never records a meeting.
- A user records a meeting but processing fails or no result is available.
- A user views a result from an old meeting imported before analytics launch.
- Browser or desktop environment blocks analytics provider access.
- Consent or workspace telemetry policy changes after events have started.
- A user or workspace deletion request arrives after aggregate reports already
  exist.
- Internal/support/test users generate events that would distort conversion
  metrics.
- Campaign attribution windows differ between ad platforms and product
  analytics dashboards.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST remain a discovery/specification effort until a
  later approved implementation slice exists.
- **FR-002**: The feature MUST define the product activation funnel before any
  product analytics code, SDK, or provider snippet is added.
- **FR-003**: The feature MUST include candidate events for
  `desktop_first_opened`, `desktop_account_connected`,
  `desktop_autorecord_enabled`, `first_recording_completed`,
  `first_result_viewed`, and `first_value_session_completed`.
- **FR-004**: The feature MUST define event owners for desktop, auth/server,
  calendar policy, capture/server, cabinet, and product analytics milestones.
- **FR-005**: The feature MUST distinguish public web intent from product
  activation and first value.
- **FR-006**: The feature MUST define whether campaign attribution can be linked
  from anonymous public analytics into authenticated/product analytics, and if
  so under which identity, consent, expiry, and deletion constraints.
- **FR-007**: The feature MUST decide a safe identity strategy before
  implementation, such as provider pseudonymous ID, server-issued hashed ID, or
  expiring campaign/session bridge token.
- **FR-008**: The feature MUST reject email, full name, organization/company
  name, workspace name, raw account ID, device name, local user path, OAuth or
  provider tokens, meeting/calendar identifiers, raw audio, transcript,
  participants, meeting title, local file paths, object keys, signed URLs,
  passwords, and passcodes as analytics fields.
- **FR-009**: The feature MUST define one B2B/B2C product telemetry gate that
  blocks normal desktop app, cabinet, and authenticated product use unless the
  user accepts the required Terms, Privacy/Personal Data processing documents,
  and mandatory bounded product telemetry package.
- **FR-010**: The feature MUST define how withdrawal, refusal of updated
  required terms, or legal/policy changes stop future product analytics events
  and limit product access to account/legal/export/deletion flows.
- **FR-011**: The feature MUST define retention and deletion truth, including
  the limits of deleting aggregate analytics already held by a provider or
  exported to reports.
- **FR-012**: The feature MUST compare provider options, including PostHog
  self-hosted, PostHog cloud, Yandex-only, and no-provider/defer options.
- **FR-012a**: The feature MUST optimize for one primary analytics workspace
  where the product owner can see the end-to-end journey from approved public
  acquisition events through first product value without routine manual exports
  or multi-dashboard reconciliation.
- **FR-012b**: The preferred provider direction is self-hosted PostHog as the
  primary full-funnel analytics home. Yandex Metrica MUST become a parallel
  all-web-pages measurement and advertising optimization surface for approved
  browser-rendered pages, and approved activation milestones MAY also be sent to
  Yandex as offline conversions when needed for ad optimization.
- **FR-012c**: The feature MUST define a parallel measurement model that uses
  both PostHog and Yandex Metrica with explicit role separation:
  PostHog receives approved full-funnel public and product activation events as
  the source of truth; Yandex Metrica receives maximum approved
  all-web-pages/ad measurement and optional approved product activation
  milestones as offline conversions for advertising optimization.
- **FR-012d**: The parallel measurement model MUST avoid routine manual exports,
  duplicated dashboard interpretation, and unbounded event fan-out. Every event
  sent to both systems must have a stated reason, allowed fields, identity rule,
  retention/deletion statement, and dashboard purpose.
- **FR-012e**: The feature MUST define a Yandex all-pages inventory covering
  public, download, legal, auth, cabinet, and authenticated product web
  surfaces. For every page class, the design MUST specify whether Yandex
  captures page views, goals/events, session parameters, user parameters,
  Webvisor/session replay, click/scroll/form maps, offline conversions, or no
  data. The target for Webvisor/session replay is full coverage on all approved
  browser-rendered page classes after masking and sanitization gates pass.
- **FR-012f**: The Yandex all-pages model MUST include URL, referrer, and page
  title sanitization rules before the Yandex tag is allowed on authenticated,
  cabinet, meeting, upload, playback, deletion, admin, or embedded desktop web
  surfaces. Raw user, workspace, meeting, calendar, file, token, object, signed
  URL, local path, and content-bearing values MUST NOT appear in Yandex-visible
  URLs, titles, parameters, events, session parameters, user parameters, or
  replay payloads.
- **FR-012g**: The feature MUST include PostHog Session Replay for approved
  browser-rendered public, auth, cabinet, and product web pages so the primary
  PostHog workspace can connect funnels, drop-offs, cohorts, and activation
  events to matching recordings. PostHog replay MUST use the same
  masking-by-default, URL/title/referrer sanitization, private DOM hiding,
  input suppression, forbidden-field controls, QA evidence, and legal review as
  Yandex Webvisor.
- **FR-013**: The feature MUST design Yandex Webvisor/session replay as
  full-coverage for all approved browser-rendered web pages, including
  authenticated product and cabinet surfaces, with masking-by-default,
  forbidden-field controls, QA evidence, legal review, and page-class launch
  blockers when a page cannot be made safe.
- **FR-014**: The feature MUST define internal/test-user filtering and support
  session exclusion before dashboards are used for campaign decisions.
- **FR-015**: The feature MUST define dashboard requirements for acquisition
  source, onboarding steps, activation, first recording, first result view, and
  first value.
- **FR-016**: The feature MUST document measurement caveats for blocked
  providers, consent rejection, direct traffic, multiple devices, duplicate
  events, failed processing, ad attribution windows, and installer downloads
  that do not prove activation.
- **FR-017**: The feature MUST define rollout gates for legal review, provider
  configuration, dashboard access, QA evidence, production smoke, and campaign
  launch.
- **FR-017a**: The rollout smoke MUST verify runtime propagation end to end:
  host env or secret source, composed service config, live container env,
  rendered HTML/JS on every approved page class, expected exclusion on blocked
  page classes, provider script reachability, and provider dashboard/goal
  visibility. A host-side `.env` value alone is not acceptable evidence.
- **FR-018**: The feature MUST preserve the `093` boundary that public
  analytics applies only to `/` and `/download` until this new feature is
  separately approved.
- **FR-019**: The feature MUST NOT add product analytics to login, cabinet,
  desktop, meetings, uploads, playback, deletion, admin, API, or embedded
  desktop surfaces as part of this specification-only backlog step.
- **FR-020**: The feature MUST produce future tasks only after clarify, plan,
  checklist, and analyze have resolved privacy, provider, identity, consent,
  deletion, and rollout blockers.
- **FR-021**: The feature MUST produce a parallel measurement matrix before
  implementation. The matrix MUST include one row per event/page milestone and
  state event name, owner, surface, PostHog destination, Yandex destination,
  Yandex mode, reason, allowed fields, forbidden fields, identity rule,
  retention/deletion truth, dashboard owner, and QA evidence.
- **FR-022**: The feature MUST produce a Yandex all-pages inventory before
  implementation. The inventory MUST cover public landing, download, legal,
  login/signup, auth callback, cabinet home, onboarding, settings, recording
  list, meeting/result detail, upload, playback, deletion, admin, embedded
  desktop webview, and error pages.
- **FR-023**: The feature MUST produce a replay masking contract before
  implementation. The contract MUST define masking-by-default behavior,
  input/form suppression, private DOM hiding, safe UI allowlisting, URL/title/
  referrer sanitization, forbidden replay payloads, QA evidence, and page-class
  launch blockers.
- **FR-024**: The feature MUST produce an identity and attribution contract
  before implementation. The contract MUST define any use of Yandex ClientID,
  `yclid`, provider pseudonymous ID, server-issued hashed ID, expiring bridge
  token, or other identifier, and MUST reject raw personal, workspace, meeting,
  device, local-path, secret, URL, and content-bearing identifiers.
- **FR-024a**: The preferred identity and attribution model MUST use a
  server-owned safe `graf_attribution_id` and/or expiring bridge token to join
  campaign context, Yandex identifiers when available, PostHog anonymous
  sessions, download intent, login/signup, account connection, and product
  activation without exposing raw identity or content-bearing values.
- **FR-024b**: The feature MUST document attribution reliability by milestone.
  `desktop_first_opened` MUST be counted even when campaign linkage is missing,
  but campaign-linked `desktop_first_opened` MUST be treated as reliable only
  when a bridge token or authenticated handoff exists. `desktop_account_connected`
  MUST be treated as the first reliable campaign-linked product milestone unless
  the implementation proves an earlier safe handoff.
- **FR-025**: The feature MUST produce a dashboard map before implementation
  that separates PostHog source-of-truth dashboards from Yandex advertising,
  web behavior, Webvisor, map, goal, and offline-conversion dashboards.
- **FR-026**: The feature MUST define launch blockers before implementation,
  including missing legal approval, missing hard telemetry gate copy, missing
  provider configuration, unsafe URL/title/referrer, unsafe unmasked DOM or
  replay region, forbidden analytics field, missing internal/test filtering,
  missing dashboard owner, missing smoke evidence, and any routine manual
  export required for daily analytics.

### Key Entities *(include if feature involves data)*

- **Product Activation Event**: A bounded product milestone event with a safe
  event name, owner, surface, allowed fields, forbidden fields, consent/notice
  requirement, identity rule, and deletion/reporting truth.
- **Campaign Attribution Link**: A privacy-reviewed connection between public
  campaign/source context and product activation, if approved. It must define
  expiry, identity, join rules, withdrawal/refusal behavior, and forbidden
  values.
- **Product Telemetry Gate**: The required consent/legal acceptance checkpoint
  that controls normal access to desktop app, cabinet, and authenticated product
  surfaces. It uses the same path for B2B/workspace and B2C users and must keep
  mandatory analytics bounded to the approved product activation contract.
- **Analytics Identity**: The safe pseudonymous or hashed identity used for
  product analytics if approved. It must not reveal email, workspace names,
  account IDs, device names, or meeting identifiers.
- **Attribution Bridge**: A server-owned safe `graf_attribution_id` and/or
  expiring bridge token that connects approved campaign context, Yandex
  identifiers when available, PostHog anonymous sessions, download intent,
  login/signup, account connection, and later activation milestones without
  exposing raw identity or content-bearing values.
- **Activation Dashboard**: A report surface that separates web intent from
  product activation and first value while excluding internal/test traffic.
- **Provider Readiness Record**: A metadata-only record of provider decision,
  hosting, legal status, dashboards, access, retention, deletion limits, and
  launch blockers.
- **Primary Analytics Workspace**: The one daily analytics home where the
  product owner reviews acquisition source, public intent, onboarding,
  activation, first recording, first result view, first value, drop-off, and
  safe cohorts without manually joining Yandex and product data.
- **Parallel Measurement Stack**: The approved two-provider analytics model.
  PostHog is the primary full-funnel workspace. Yandex Metrica is the
  all-web-pages measurement and ad optimization workspace. Shared events are
  limited to approved public acquisition events and approved product activation
  milestones that have a specific advertising or attribution purpose.
- **Yandex All-Pages Inventory**: A required page-by-page approval table for
  all browser-rendered surfaces. It states the Yandex collection mode, allowed
  fields, forbidden fields, URL/title sanitization, replay/map setting, identity
  rule, legal basis, retention/deletion statement, and dashboard purpose for
  each page class.
- **Replay Masking Contract**: A shared masking and sanitization contract for
  both PostHog Session Replay and Yandex Webvisor. It defines which page
  classes may replay, which DOM/input/title/URL/referrer data is suppressed,
  which safe UI regions may remain visible, what evidence is required, and what
  blocks launch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A product owner can review one approved funnel that separates
  installer download intent, first app open, account connection, auto-record
  enablement, first recording, first result view, and first value.
- **SC-002**: 100% of proposed activation events have an owner, surface,
  allowed field set, forbidden field set, consent/notice rule, identity rule,
  and deletion/reporting statement before implementation tasks are generated.
- **SC-003**: 0 forbidden private/content-bearing fields are approved in the
  event contract.
- **SC-004**: A privacy/product reviewer can decide whether campaign attribution
  may be linked to product activation without reading application code.
- **SC-005**: A provider decision record clearly explains the selected provider
  or deferral decision, hosting model, egress boundary, retention, deletion
  participation, replay status, and dashboard ownership.
- **SC-005a**: A product owner can open one primary workspace and inspect the
  approved full journey from campaign/source to first value without using a
  manual spreadsheet export, a custom ETL job, or a second dashboard as the
  source of truth.
- **SC-005b**: A product owner can move from a PostHog funnel, cohort, or
  drop-off segment into matching approved session recordings inside PostHog
  without manual ID matching or opening Yandex for the primary product
  investigation.
- **SC-005c**: A campaign report can distinguish counted `desktop_first_opened`
  from campaign-linked `desktop_first_opened` and campaign-linked
  `desktop_account_connected`, so dashboards do not overstate installer-to-app
  attribution.
- **SC-006**: A rollout checklist blocks implementation or launch when legal
  review, the hard product telemetry gate, identity, provider configuration,
  dashboard access, QA evidence, internal/test filtering, or production smoke is
  missing.
- **SC-006a**: Production smoke evidence proves that analytics provider
  settings reach the intended runtime service and rendered pages, and that
  disallowed surfaces do not accidentally receive analytics code.
- **SC-007**: Campaign reports can distinguish web intent from real product
  activation and first value, including documented caveats for consent,
  blocking, duplicates, direct traffic, and failed processing.

## Assumptions

- Feature `093-public-landing-analytics` remains the current public web
  analytics baseline and is not expanded by this backlog feature.
- Public analytics is limited to `/` and `/download` until this feature
  completes a separate high-risk Spec Kit flow and implementation approval.
- As of the 093 production closeout, public Yandex Metrica is live only for
  `/` and `/download`; this does not authorize app/cabinet/authenticated
  analytics without the separate 094 flow.
- Product activation analytics is high-risk because it touches desktop,
  authentication, recording, cabinet, privacy, deletion truth, provider egress,
  and campaign decisions.
- Self-hosted PostHog is the preferred primary full-funnel analytics direction,
  but the final provider decision still requires research and legal/operations
  gates.
- Yandex Metrica is risk-accepted as a future all-web-pages measurement surface
  for public, legal, auth, cabinet, and authenticated product web pages, but it
  should not be the daily source of truth for product activation unless a later
  provider decision explicitly rejects PostHog.
- Enabling Yandex on authenticated and product pages requires proof that URL,
  referrer, page title, event, session parameter, user parameter, replay, and
  map payloads cannot contain forbidden identity, meeting, file, secret, local
  path, or content-bearing data.
- Yandex Webvisor/session replay is risk-accepted as a full-coverage target for
  all approved browser-rendered web pages, but only with masking-by-default,
  URL/title/referrer sanitization, forbidden-field controls, QA evidence, legal
  review, and no meeting/content-bearing payloads.
- Legal copy, personal-data consent, operator notice, and cross-border/provider
  review must be updated before product telemetry launch.
- Required product telemetry may be mandatory for normal product use only when
  it remains bounded to safe activation analytics and masked/sanitized Yandex
  replay. It must exclude unmasked product replay, ad retargeting, raw
  identities, meeting content, local paths, secrets, and all other forbidden
  fields.
- Implementation, provider setup, production smoke, and campaign optimization
  are out of scope for this backlog capture.
