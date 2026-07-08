# Feature Specification: Product Activation Analytics

**Feature Branch**: `094-product-activation-analytics`

**Created**: 2026-07-08

**Status**: Draft backlog feature for future SDD/Spec Kit discovery

**Input**: User description: "Зафиксировать отдельную будущую фичу для продуктовой аналитики приложения GRAF. Передать весь контекст из `093-public-landing-analytics`, где публичная аналитика уже ограничена `/` и `/download`, а приложение/кабинет/встречи специально не трекаются. Нужна SDD-проработка before implementation: provider, identity, consent/notice, retention/deletion truth, forbidden fields, dashboards, legal readiness, rollout gates."

## SDD Carry-Forward Prompt

Use `specs/094-product-activation-analytics/sdd-prompt.md` as the prompt for
the next SDD pass. The prompt intentionally asks for discovery and decisions,
not implementation.

## Context From Feature 093

Feature `093-public-landing-analytics` completed public web analytics only:

- public surfaces: `/` and `/download`;
- provider: Yandex Metrica, disabled by default in runtime env;
- no Google/GA4/GTM in Phase 1;
- no PostHog/product analytics code in Phase 1;
- consent-first public analytics with CookieConsent v3.1.0;
- Webvisor/replay only for public pages and only with `behavior_replay`
  consent;
- primary web conversion: `public_installer_download_clicked`;
- secondary web steps: landing view, section reach, CTA click, download page
  view, login intent;
- legal pages exist as draft copy and paid campaign launch remains blocked
  until legal review, dashboard setup, and live provider smoke are separately
  approved.

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

**Independent Test**: Review the future plan and confirm it defines consent or
notice, opt-out behavior, identity linkage, forbidden fields, deletion truth,
and internal/test-user filtering before implementation tasks exist.

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
- **FR-009**: The feature MUST define consent, notice, opt-out, and workspace
  policy behavior before implementation.
- **FR-010**: The feature MUST define how consent or policy changes stop future
  product analytics events.
- **FR-011**: The feature MUST define retention and deletion truth, including
  the limits of deleting aggregate analytics already held by a provider or
  exported to reports.
- **FR-012**: The feature MUST compare provider options, including PostHog
  self-hosted, PostHog cloud, Yandex-only, and no-provider/defer options.
- **FR-013**: The feature MUST decide whether product session replay is out of
  scope, forbidden, or separately gated; meeting/cabinet replay MUST NOT be
  assumed from public landing replay.
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
- **FR-018**: The feature MUST preserve the `093` boundary that public
  analytics applies only to `/` and `/download` until this new feature is
  separately approved.
- **FR-019**: The feature MUST NOT add product analytics to login, cabinet,
  desktop, meetings, uploads, playback, deletion, admin, API, or embedded
  desktop surfaces as part of this specification-only backlog step.
- **FR-020**: The feature MUST produce future tasks only after clarify, plan,
  checklist, and analyze have resolved privacy, provider, identity, consent,
  deletion, and rollout blockers.

### Key Entities *(include if feature involves data)*

- **Product Activation Event**: A bounded product milestone event with a safe
  event name, owner, surface, allowed fields, forbidden fields, consent/notice
  requirement, identity rule, and deletion/reporting truth.
- **Campaign Attribution Link**: A privacy-reviewed connection between public
  campaign/source context and product activation, if approved. It must define
  expiry, identity, join rules, opt-out behavior, and forbidden values.
- **Product Telemetry Preference**: The consent, notice, workspace policy, or
  admin setting that controls future product analytics events.
- **Analytics Identity**: The safe pseudonymous or hashed identity used for
  product analytics if approved. It must not reveal email, workspace names,
  account IDs, device names, or meeting identifiers.
- **Activation Dashboard**: A report surface that separates web intent from
  product activation and first value while excluding internal/test traffic.
- **Provider Readiness Record**: A metadata-only record of provider decision,
  hosting, legal status, dashboards, access, retention, deletion limits, and
  launch blockers.

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
- **SC-006**: A rollout checklist blocks implementation or launch when legal
  review, consent/notice, identity, provider configuration, dashboard access,
  QA evidence, internal/test filtering, or production smoke is missing.
- **SC-007**: Campaign reports can distinguish web intent from real product
  activation and first value, including documented caveats for consent,
  blocking, duplicates, direct traffic, and failed processing.

## Assumptions

- Feature `093-public-landing-analytics` remains the current public web
  analytics baseline and is not expanded by this backlog feature.
- Public analytics is limited to `/` and `/download` until this feature
  completes a separate high-risk Spec Kit flow and implementation approval.
- Product activation analytics is high-risk because it touches desktop,
  authentication, recording, cabinet, privacy, deletion truth, provider egress,
  and campaign decisions.
- PostHog is a candidate provider, not an approved provider.
- Self-hosted provider options are preferred for privacy review, but the
  decision must be made through research and legal/operations gates.
- Product session replay is not assumed; if considered, it requires a separate
  privacy review and must not capture meeting content.
- Legal copy, operator notice, and cross-border/provider review must be updated
  before product telemetry launch.
- Implementation, provider setup, production smoke, and campaign optimization
  are out of scope for this backlog capture.
