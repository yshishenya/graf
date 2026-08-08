# Feature Specification: Product Analytics Provider Rollout

**Feature Branch**: `096-product-analytics-provider-rollout`

**Created**: 2026-07-09

**Status**: Integrated and released; T101 operational acceptance and T104 final closeout remain open

**Input**: User description: "Start feature 096-product-analytics-provider-rollout after 094. Set up a production-ready provider layer for product activation analytics: self-hosted PostHog as the primary workspace, Yandex Metrica as the parallel web/ad/Webvisor/offline-conversion surface, runtime secret/config wiring without live secrets in git, provider smoke, dashboard readiness, rollback, and legal/campaign blockers. Keep this separate from 094 implementation."

## Clarifications

### Session 2026-07-09

- Q: What delivery posture should 096 use for self-hosted PostHog now that it is inside the owner-controlled GRAF contour? -> A: Treat self-hosted PostHog as a first-party, owner-controlled analytics workspace and send the maximum useful product analytics to it, including server, web-direct, and desktop-direct routes. Because PostHog is inside the owner-controlled GRAF contour, product-visible data that GRAF can already display may be treated as internal content-bearing product analytics for PostHog when retention, RBAC, audit, deletion-truth, disclosure, no-secret, smoke, and rollback controls exist. This broader PostHog posture does not apply to Yandex or any other external advertising surface. Security credential material remains forbidden everywhere: passwords, passcodes, OAuth codes, access/refresh/id tokens, API keys, signed URLs, cookies, provider/client secrets, private keys, raw audio files, and raw committed payload dumps must not be captured, committed, or used as evidence.
- Q: Which Yandex counter strategy should 096 use, and should it support all current and future pages? -> A: Reuse the existing production Yandex counter from 093 as the expandable all-pages Yandex surface. Preserve the currently live approved public scope on `/` and `/download`, then allow 096 to expand the same counter to every current browser-rendered page class and every future page only through a mandatory page-class inventory. Each current or future page class must have an explicit state before collection: approved safe page view/event collection, blocked, or replay-unavailable with Webvisor/click map/scroll map/form analytics disabled. Future pages default to blocked for Yandex collection until they are added to the inventory with URL/title/referrer/event-field sanitization, forbidden-field review, legal/QA status, dashboard purpose, and rollback behavior.
- Q: Where should self-hosted PostHog run for the first production rollout? -> A: Start PostHog on the same production server as GRAF, but expose it through a separate analytics domain and keep it operationally portable. The 096 runbook must isolate PostHog by service, domain/TLS, secret files, volumes, backups, resource limits, health checks, and rollback switches so it can be moved later to a separate analytics server without changing event names, client contracts, dashboard definitions, consent copy, or provider-facing configuration beyond DNS/runtime endpoint updates.
- Q: Should PostHog autocapture be enabled everywhere immediately because PostHog is inside the owner-controlled contour? -> A: Yes. 096 must enable PostHog autocapture everywhere immediately for all current browser-rendered GRAF pages and make that the default for future browser-rendered pages. This is intentional product-learning behavior, not an accidental side effect: PostHog should capture broad click/path/navigation/element behavior across public, auth, cabinet, meeting/result/detail, upload, deletion, admin, error, legal, onboarding, settings, and embedded webview page classes because the workspace is owned and operated by GRAF. Page-class inventory is still required, but it records sensitivity, disclosure, retention/deletion truth, rollback, and any required credential sanitization instead of blocking PostHog autocapture by default. PostHog autocapture does not automatically enable PostHog session replay or Yandex Webvisor/maps/forms; those remain separate capabilities. Security credential material remains forbidden everywhere and must be removed or suppressed before capture.
- Q: Should Yandex offline conversions be uploaded live in 096 or kept dry-run? -> A: Enable live Yandex offline conversion upload in 096 for exactly `desktop_account_connected` and `first_value_session_completed`. This live upload requires OAuth token secret-file wiring, duplicate protection, attribution-window caveats, provider smoke, dashboard visibility, legal/security/QA approval, rollback proof, and metadata-only evidence. No additional product milestones may be uploaded to Yandex in 096. Paid campaign launch remains blocked separately.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operate Primary Product Analytics Workspace (Priority: P1)

An operator and product owner need a production-ready self-hosted PostHog workspace that can receive the approved 094 product activation events and broad first-party product analytics without using PostHog Cloud, credential material, or unsafe committed evidence.

**Why this priority**: PostHog is the primary full-funnel analytics home. Without a self-hosted, backed-up, secret-safe workspace, the activation funnel cannot leave scaffold mode.

**Independent Test**: Review the provider runbook, runtime configuration inventory, secret inventory, retention statement, rollback plan, and provider smoke evidence to confirm that PostHog can be operated without committing live secrets or private payloads.

**Acceptance Scenarios**:

1. **Given** the approved 094 activation event catalog, **When** the PostHog provider layer is configured, **Then** only approved event names and approved metadata fields can be delivered.
2. **Given** a production PostHog workspace is needed, **When** rollout evidence is reviewed, **Then** the evidence identifies same-server placement, separate analytics domain, TLS status, container operations, backup/restore, resource limits, portability plan, and at least 90 days of analytics retention.
3. **Given** the PostHog project key and internal secrets exist outside git, **When** runtime wiring is validated, **Then** secret files and service environment propagation are proven without exposing live values.
4. **Given** PostHog autocapture is part of product learning, **When** 096 is evaluated, **Then** autocapture is enabled for every browser-rendered GRAF page by default, while security credential material is suppressed and replay remains a separate capability.

---

### User Story 2 - Extend Yandex Measurement Without Breaking 093 Boundaries (Priority: P1)

A growth owner needs Yandex Metrica to remain the public web/ad attribution surface from 093 while preparing product activation offline conversions and a safe all-pages inventory.

**Why this priority**: Public Yandex analytics is already live for `/` and `/download`. 096 must preserve that production boundary while adding offline-conversion readiness and deciding counter strategy without leaking product data.

**Independent Test**: Review the Yandex setup/runbook, counter decision record, offline conversion contract, all-pages inventory, OAuth secret handling, and rendered-page scope evidence.

**Acceptance Scenarios**:

1. **Given** 093 public analytics is live for `/` and `/download`, **When** 096 is configured, **Then** those public surfaces remain approved and the same existing production counter becomes the expandable all-pages Yandex surface for approved current and future page classes.
2. **Given** Yandex Direct attribution and offline conversion linkage need continuity from public acquisition to product activation, **When** counter strategy is documented, **Then** the record explains that the existing production counter is reused and that every non-public or future page class must pass the 096 inventory gates before collection.
3. **Given** product milestones are sent to Yandex, **When** offline conversion rollout is reviewed, **Then** live upload is enabled only for `desktop_account_connected` and `first_value_session_completed`.
4. **Given** Yandex OAuth credentials are needed, **When** runtime wiring is validated, **Then** the token is available only through a secret file and no token, counter ID, client ID, cookie, or visitor identifier is committed.

---

### User Story 3 - Govern Broad PostHog Autocapture And High-Risk Surfaces (Priority: P1)

A privacy/product reviewer needs proof that broad PostHog autocapture is intentional, disclosed, owner-controlled, reversible, and separated from Yandex/Webvisor/replay behavior.

**Why this priority**: Provider setup touches sensitive authenticated pages, product activity, account workflows, meeting review, attribution links, and internal content-bearing analytics. The risk is not that GRAF cannot see its own product data; the risk is ungoverned collection, credential capture, unclear retention/deletion truth, or accidentally treating Yandex/external advertising surfaces like first-party PostHog.

**Independent Test**: Review the page-class inventory, PostHog autocapture policy, credential-suppression rules, replay/Webvisor separation, direct desktop egress controls, dashboard caveats, RBAC/retention/deletion statements, rollback plan, and metadata-only smoke/evidence scans.

**Acceptance Scenarios**:

1. **Given** any current browser-rendered GRAF page, **When** 096 is enabled, **Then** PostHog autocapture is active for that page and the page inventory records sensitivity, expected product-visible data, credential-suppression rules, retention/deletion truth, owner, dashboard purpose, and rollback behavior.
2. **Given** an admin page, auth callback, meeting/result/detail page, deletion page, upload page, or embedded desktop webview exists, **When** PostHog autocapture runs, **Then** it remains allowed as first-party internal product analytics while credential material, signed URLs, provider secrets, cookies, passcodes, and raw payload evidence are suppressed or excluded.
3. **Given** PostHog session replay, Yandex Webvisor, click maps, scroll maps, or form analytics are requested, **When** rollout scope is evaluated, **Then** those capabilities are treated separately from PostHog autocapture and still require their own page-class approval.
4. **Given** the desktop app emits product analytics, **When** delivery is evaluated, **Then** direct desktop delivery to self-hosted PostHog is allowed as a first-party route with disclosure, identity rules, no-secret validation, provider smoke, retry/loss rules, and rollback proof; direct desktop delivery to Yandex remains blocked unless separately approved.

---

### User Story 4 - Prove Rollback, Dashboards, And Blockers Before Rollout Claims (Priority: P2)

An operator needs clear smoke, dashboard evidence, rollback steps, and blocker status before anyone treats provider setup as product rollout readiness or campaign launch readiness.

**Why this priority**: Provider dashboards can mislead product and campaign decisions if smoke evidence, retention, legal blockers, rollback, and caveats are incomplete.

**Independent Test**: Review the provider smoke output, dashboard evidence template, rollback plan, legal/campaign blocker record, and implementation evidence for metadata-only proof.

**Acceptance Scenarios**:

1. **Given** provider delivery is smoke-tested, **When** evidence is recorded, **Then** it uses dry-run or live-safe synthetic payloads with no private visitor, account, meeting, transcript, audio, token, cookie, local path, or signed URL data.
2. **Given** dashboards are prepared, **When** readiness is reviewed, **Then** every dashboard has an owner, purpose, event/page coverage, retention/deletion caveat, internal/test activity caveat, and provider delivery-gap caveat.
3. **Given** provider setup passes, **When** release status is written, **Then** paid campaign launch and product rollout readiness remain blocked until their separate legal/product/security/QA approvals exist.
4. **Given** provider rollout must be reversed, **When** rollback is executed or rehearsed, **Then** the system can disable provider delivery, replay, offline uploads, and page expansion while preserving normal product workflows.

### Edge Cases

- The existing 093 Yandex counter supports public analytics but cannot safely support product offline conversions without exposing product identifiers.
- Yandex Direct attribution requires the same counter for campaign linkage, but separate product reporting would be simpler operationally.
- A provider project key, internal secret, or OAuth token is missing, malformed, expired, mounted into the wrong service, or accidentally present in committed files.
- PostHog or Yandex is reachable from the host but not from the live service runtime.
- PostHog shares the production server with GRAF and starts consuming too much CPU, memory, disk, or network capacity.
- PostHog must be moved from the shared production server to a separate analytics server after dashboards and events are already live.
- Provider smoke succeeds in dry-run mode but live-safe delivery is blocked by provider configuration, network policy, or dashboard permissions.
- A rendered page includes Yandex analytics configuration on a blocked Yandex page class.
- A new browser-rendered page ships after 096 without being added to the Yandex page-class inventory.
- A PostHog-autocaptured page later adds a credential-bearing URL, OAuth callback code, signed download URL, cookie-like value, token-like form field, or provider secret.
- A replay-approved page later adds a private DOM region, form, title, URL segment, or referrer value that invalidates replay masking proof.
- Offline conversion upload is retried after provider outage and risks duplicates or attribution-window mismatch.
- A user or workspace deletion request arrives after provider-held aggregate reports, exported dashboards, or offline conversions already exist.
- Internal, support, smoke, or test activity appears in provider dashboards.
- Legal, personal-data operator, campaign-readiness, or disclosure approval is missing after technical smoke passes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST remain a separate 096 provider/infrastructure rollout after 094 and MUST NOT mark 094 itself as live provider setup, deploy, all-pages Yandex rollout, offline upload, direct desktop provider egress, replay rollout, or paid campaign launch.
- **FR-002**: The feature MUST configure self-hosted PostHog as the primary product analytics workspace and MUST NOT use PostHog Cloud for this rollout.
- **FR-003**: The PostHog rollout MUST deploy initially on the same production server as GRAF while using a separate analytics domain, separate TLS/runtime routing, separate service boundaries, separate secret files, separate volumes, resource limits, retention policy, dashboard access model, health checks, and rollback path.
- **FR-003a**: The PostHog rollout MUST be portable to a separate analytics server later. The runbook MUST document what moves, what stays stable, and what changes during migration: DNS, TLS, service endpoint, volumes/backups/restore, secrets, firewall/network rules, smoke checks, dashboard continuity, provider endpoint configuration, and rollback. Event names, approved field contracts, identity rules, consent copy, dashboard definitions, and product-side analytics contracts MUST remain stable across the move.
- **FR-003b**: The same-server PostHog runbook MUST define concrete initial CPU, memory, disk, network, log-retention, backup-retention, disk-full, and alert/review thresholds, plus the evidence required to show that analytics load causes a measurement degradation or rollback before it can starve normal GRAF product workflows.
- **FR-004**: Self-hosted PostHog MUST be treated as a first-party owner-controlled analytics workspace for this rollout. The design MUST send the maximum useful product analytics to PostHog, including activation events, public acquisition events, page views/events, broad autocapture, safe cohorts/properties, delivery-gap metadata, dashboard readiness metadata, route diagnostics, and product-visible content-bearing behavior needed for product learning.
- **FR-004a**: PostHog autocapture MUST be enabled everywhere immediately for every current browser-rendered GRAF page and MUST be the default expectation for every future browser-rendered page. This includes public, download, legal, login/signup, auth callback, cabinet, onboarding, settings, recording list, meeting/result/detail, upload, playback, deletion, admin, embedded desktop webview, and error page classes.
- **FR-004b**: PostHog delivery MAY use server-mediated, web-direct, and desktop-direct routes because PostHog is first-party and owner-controlled. Each route MUST still declare disclosure, identity rules, RBAC/audit expectations, retention/deletion truth, provider smoke, retry/loss behavior, rollback evidence, and dashboard caveats.
- **FR-004c**: Server-mediated PostHog delivery MUST remain available for events or identity handoffs that need server validation, attribution bridging, dedupe, lifecycle accounting, deletion truth, or delivery-gap reporting, but lack of server mediation MUST NOT by itself block web-direct or desktop-direct PostHog analytics.
- **FR-004d**: PostHog may store content-bearing internal product analytics from browser-rendered product pages because it is owner-controlled. This allowance is limited to PostHog and MUST NOT be copied to Yandex, paid advertising platforms, committed evidence, logs, screenshots, or raw payload dumps.
- **FR-005**: PostHog session replay MAY be enabled only for a page class with masking-by-default proof, URL/title/referrer sanitization proof, form/input suppression, private DOM hiding, QA evidence, legal approval, and dashboard caveat approval.
- **FR-005a**: PostHog autocapture MUST NOT be treated as PostHog session replay. Autocapture is enabled broadly in 096; session replay remains a separate feature flag and page-class state.
- **FR-005b**: Security credential material MUST be forbidden everywhere, including first-party PostHog autocapture. The rollout MUST suppress or remove passwords, passcodes, OAuth codes, access/refresh/id tokens, API keys, signed URLs, cookies, provider/client secrets, private keys, raw audio files, and raw payload dumps before capture, storage, logs, screenshots, dashboards, or evidence.
- **FR-006**: PostHog project keys and internal provider secrets MUST be supplied only through runtime secret files or equivalent out-of-git secret mounts, and committed docs/tests/evidence MUST contain only placeholders or redacted metadata.
- **FR-007**: The feature MUST preserve the 093 Yandex public scope on `/` and `/download` as the currently live approved baseline while allowing 096 to expand Yandex collection through the same production counter only for page classes approved by the 096 inventory.
- **FR-008**: The feature MUST reuse the existing production Yandex counter from 093 as the expandable all-pages Yandex surface for acquisition, Yandex Direct attribution, approved safe page views/events, Webvisor/map/form capabilities after proof, and approved offline conversions. A separate product counter is not the default for 096 and may be introduced only if planning proves the existing counter cannot safely support the required attribution and page-class controls.
- **FR-009**: Yandex offline conversion live upload MUST be enabled in 096 for exactly `desktop_account_connected` and `first_value_session_completed`; any additional product milestone requires a later explicit approval.
- **FR-009a**: Yandex offline conversion live upload MUST require OAuth token secret-file wiring, duplicate protection, attribution-window caveats, provider smoke, dashboard visibility, legal/security/QA approval, rollback proof, and metadata-only evidence before it is considered ready.
- **FR-009b**: Yandex offline conversion `UserId` upload MUST require proof that the same GRAF pseudonymous user ID was sent to Yandex during an eligible counted browser session through `setUserID` and `userParams`. `ClientId` and `Yclid` uploads MUST require real runtime resolver values and MUST NOT be synthesized from the GRAF pseudonymous user ID.
- **FR-010**: Yandex OAuth tokens and upload credentials MUST be supplied only through runtime secret files or equivalent out-of-git secret mounts.
- **FR-011**: The feature MUST prepare a Yandex all-pages inventory for public landing, download, legal, login/signup, auth callback, cabinet, onboarding, settings, recording list, meeting/result/detail, upload, playback, deletion, admin, embedded desktop webview, and error page classes.
- **FR-011a**: The Yandex all-pages inventory MUST be extensible. Every future browser-rendered page class must be added to the inventory before Yandex collection is allowed, with explicit state, allowed events/fields, forbidden-field review, URL/title/referrer sanitization status, replay/map/form status, legal/QA status, dashboard purpose, and rollback behavior. Missing inventory means Yandex collection is blocked for that page class by default.
- **FR-012**: Auth callback and admin page classes MUST remain blocked by default for Yandex collection. They MUST be included in PostHog autocapture as first-party product analytics only after global credential-suppression rules are in place.
- **FR-013**: Meeting/result/detail PostHog autocapture MUST be enabled as first-party internal product analytics in 096, but PostHog session replay and Yandex Webvisor/map/form analytics for meeting/result/detail pages MUST remain unavailable until separate replay proof exists.
- **FR-014**: Yandex Webvisor, PostHog session replay, click maps, scroll maps, and form analytics MUST require page-class masking proof before activation; these proof requirements do not block first-party PostHog autocapture.
- **FR-015**: Provider smoke MUST prove runtime propagation from secret/config source through service runtime and rendered/provider surfaces, and MUST use only dry-run or live-safe synthetic payloads with no private data.
- **FR-016**: Dashboard readiness evidence MUST identify owner, purpose, event/page scope, retention/deletion caveat, internal/test activity caveat, provider delivery-gap caveat, and campaign interpretation caveat for every dashboard.
- **FR-017**: The feature MUST include a secret inventory and env propagation tests covering PostHog project key, PostHog internal secrets, Yandex counter/runtime config, Yandex OAuth token, validation mode, replay flags, offline upload flags, and provider enablement flags.
- **FR-018**: The feature MUST include a rollback plan that can disable PostHog delivery, PostHog autocapture, Yandex page expansion, replay/map/form collection, offline conversion upload, and provider validation modes without blocking normal product workflows after telemetry acceptance.
- **FR-019**: The feature MUST record legal, privacy, security, QA, campaign-readiness, and disclosure blockers separately from technical provider smoke and MUST NOT treat provider setup as product rollout readiness.
- **FR-020**: The feature MUST NOT enable paid campaign launch.
- **FR-021**: The feature MAY enable direct desktop delivery to self-hosted PostHog as a first-party route for product analytics after telemetry disclosure, identity rules, no-secret validation, provider smoke, retry/loss rules, and rollback proof. Direct desktop delivery to Yandex remains blocked unless a later explicit approval adds it.
- **FR-022**: Committed artifacts MUST NOT contain live counter IDs, PostHog project keys, OAuth tokens, cookies, client IDs, visitor IDs, raw payloads, screenshots with visitor/account data, names, emails, local paths, signed URLs, meeting content, transcript text, audio, private identifiers, or any content-bearing PostHog autocapture export. Content-bearing analytics may exist inside the self-hosted PostHog workspace, but committed evidence remains metadata-only.
- **FR-023**: The feature MUST produce metadata-only implementation evidence that lists validation commands, smoke status, provider/dashboard readiness status, blockers, rollback status, and no-secret scan results.
- **FR-024**: The feature MUST include infra docs/runbook for PostHog, a Yandex provider setup/runbook, provider smoke scripts, dashboard evidence template, rollback plan, implementation evidence, and supporting Spec Kit plan/checklist/tasks/analyze/task-to-issues artifacts before implementation closeout.

### Key Entities *(include if feature involves data)*

- **Provider Rollout Record**: Metadata-only status for PostHog and Yandex setup, including scope, owner, runtime mode, smoke result, dashboard readiness, blockers, and rollback state.
- **PostHog Workspace**: Self-hosted primary analytics workspace for approved public acquisition and 094 product activation events. The first rollout runs on the same production server as GRAF under a separate analytics domain, with retention, access, backup/restore, secret, replay, resource-limit, portability, and rollback controls.
- **PostHog Delivery Route**: A server-mediated, web-direct, or desktop-direct route into the self-hosted PostHog workspace. Each route must declare owner, surface, event/autocapture behavior, identity rule, disclosure/legal/QA status, smoke evidence, retry/loss behavior, rollback path, RBAC/audit expectations, retention/deletion truth, and credential-material exclusions.
- **Yandex Measurement Surface**: The existing production Yandex counter from 093 reused as the expandable all-pages counter for approved public pages, approved safe page views/events, optional offline conversions, and Webvisor/map/form capabilities only after proof.
- **Provider Secret Inventory**: The list of provider keys, OAuth tokens, internal secrets, runtime flags, owners, storage locations, rotation expectations, and propagation checks, recorded without live secret values.
- **Page-Class Inventory**: Approval matrix for each current and future browser-rendered class, including PostHog autocapture state, Yandex collection mode, replay/map/form state, credential-suppression rules, sensitivity notes, legal basis, dashboard purpose, rollback behavior, and caveats. New pages default to PostHog autocapture enabled once global credential suppression exists, while Yandex collection stays blocked until the inventory approves it.
- **Offline Conversion Contract**: The approved Yandex offline conversion subset, identity/attribution rule, duplicate handling, attribution-window caveat, upload mode, token source, and evidence boundary.
- **Replay Proof Record**: Page-class proof that masking, hidden DOM, input suppression, URL/title/referrer sanitization, and forbidden-field controls pass before replay/map/form collection.
- **Autocapture Governance Record**: Proof that broad PostHog autocapture is intentional and governed for a page class, including expected product-visible data, credential-suppression rules, sensitivity label, dashboard caveats, owner approval, retention/deletion truth, RBAC/audit expectations, and rollback behavior.
- **Provider Smoke Result**: Dry-run or live-safe validation result proving delivery wiring and dashboard visibility without private payloads.
- **Dashboard Readiness Record**: Metadata-only proof that each provider dashboard has an owner, purpose, coverage statement, caveats, and blocker status.
- **Rollback Plan**: Operator procedure and evidence for disabling provider delivery, replay/map/form collection, all-pages expansion, offline upload, and validation modes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of provider secrets and runtime IDs referenced by the rollout have an owner, storage source, propagation test, rotation note, and redacted evidence entry, with 0 live values committed.
- **SC-002**: PostHog provider smoke proves server-mediated, web-direct, desktop-direct, and everywhere-autocapture routes can be delivered or dry-run validated, while security credential material is suppressed and no content-bearing payload samples are committed.
- **SC-003**: The PostHog runbook documents same-server placement, separate analytics domain, TLS, operations, backup, restore, concrete resource limits and alert thresholds, retention of at least 90 days, health checks, rollback, and later move-out procedure before provider enablement is considered ready.
- **SC-004**: Yandex offline conversion live upload sends exactly `desktop_account_connected` and `first_value_session_completed`, with no additional product event enabled.
- **SC-005**: 100% of current browser-rendered page classes have PostHog autocapture enabled or explicitly marked non-browser/not-rendered, plus a Yandex state of approved, blocked, or replay-unavailable; future browser-rendered page classes inherit PostHog autocapture by default after credential-suppression rules exist and keep Yandex blocked until inventory approval.
- **SC-006**: Auth callback, admin, and meeting/result/detail pages are included in first-party PostHog autocapture with credential suppression and metadata-only evidence, while Yandex collection and PostHog replay for those classes remain blocked or unavailable until their separate proof exists.
- **SC-007**: Provider smoke verifies runtime propagation beyond host-side files: secret/config source, service runtime, rendered pages or delivery endpoint, provider reachability, and dashboard/goal visibility where applicable.
- **SC-008**: Dashboard evidence covers every provider dashboard with owner, purpose, event/page scope, retention/deletion caveat, internal/test activity caveat, provider gap caveat, and campaign caveat.
- **SC-009**: Rollback evidence demonstrates that provider delivery, PostHog autocapture, Yandex all-pages expansion, replay/map/form collection, offline upload, and provider validation mode can be disabled without blocking normal product workflows.
- **SC-010**: Implementation evidence records legal, campaign, disclosure, security, and QA blockers separately from technical smoke; paid campaign launch and product rollout readiness remain blocked unless separately approved.
- **SC-011**: PostHog autocapture is enabled everywhere for current browser-rendered pages, evidence shows credential material is suppressed, and no raw content-bearing autocapture payloads, screenshots, visitor/account data, meeting content, transcript text, local paths, signed URLs, object keys, tokens, cookies, or form values are committed.

## Assumptions

- Feature 094 is the safe product analytics scaffold baseline and remains disabled-by-default until 096 or later rollout gates approve provider delivery.
- Feature 093 public Yandex analytics for `/` and `/download` remains the current production-approved public scope.
- The existing 093 production Yandex counter is the preferred 096 counter so acquisition, Yandex Direct attribution, safe all-pages measurement, and offline conversions can grow in one place under explicit page-class gates.
- The first PostHog production rollout uses the existing production server with a separate analytics domain, but must be designed so it can move later to a separate analytics server through DNS/runtime endpoint, backup/restore, secret, and smoke changes without changing event contracts.
- Minimum approved analytics retention is 90 days unless legal/security requires a shorter category for replay, offline conversions, bridge records, or exported reports.
- Provider setup can prove technical readiness, but it is not enough to claim product rollout readiness or campaign launch readiness.
- Internal, support, smoke, and test activity may appear in dashboards by default and must be disclosed rather than silently filtered in this feature.
- PostHog autocapture is intentionally broad because PostHog is self-hosted inside the owner-controlled contour; Yandex and paid advertising surfaces do not inherit this broader first-party allowance.
- Direct desktop provider egress to self-hosted PostHog is allowed in 096 as an explicitly disclosed, tested, rollback-safe first-party route; direct desktop provider egress to Yandex remains blocked unless a later explicit approval expands the route.
