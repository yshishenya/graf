# Research: Product Activation Analytics

**Feature**: `094-product-activation-analytics`

**Lane**: high-risk Spec Kit planning. This research supports planning and does
not authorize implementation.

## Research Sources

- PostHog self-host docs: https://posthog.com/docs/self-host
- PostHog open-source self-host disclaimer: https://posthog.com/docs/self-host/open-source/disclaimer
- PostHog self-host egress docs: https://posthog.com/docs/self-host/configure/egress
- PostHog privacy controls: https://posthog.com/docs/privacy
- PostHog data collection controls: https://posthog.com/docs/privacy/data-collection
- PostHog Session Replay privacy controls: https://posthog.com/docs/session-replay/privacy
- PostHog Session Replay storage: https://posthog.com/docs/self-host/configure/session-replay-storage
- PostHog capture events and identity docs: https://posthog.com/docs/product-analytics/capture-events and https://posthog.com/docs/product-analytics/identify
- PostHog schema management: https://posthog.com/docs/product-analytics/schema-management
- Yandex Metrica offline conversions: https://yandex.com/support/metrica/en/data/offline-params
- Yandex Metrica confidential data guidance: https://yandex.com/support/metrica/en/general/confidential-data
- Yandex Metrica GDPR/privacy controls: https://yandex.com/support/metrica/en/general/gdpr
- Yandex Metrica Webvisor settings: https://yandex.ru/support/metrica/en/webvisor/settings
- Yandex Metrica event/session parameters: https://yandex.com/support/metrica/en/data/visit-params-data
- Yandex Metrica Terms/DPA: https://yandex.com/legal/metrica_termsofuse/en/ and https://yandex.com/legal/metrica_agreement/en/

## Decision: Use Self-Hosted PostHog As Primary Product Workspace, Gated

Self-hosted PostHog remains the preferred primary product activation workspace,
provided operations, security, legal, storage, retention, and support gates pass.
It receives approved public acquisition context plus approved product activation
events and owns daily funnels, cohorts, retention, drop-off, first-value reports,
and funnel-to-session-replay investigation.

**Rationale**:

- The product owner needs one daily workspace for the full journey from source
  to first value.
- PostHog supports explicit product analytics events, identified users, funnels,
  retention, cohorts, session replay, schema management, and privacy controls.
- Self-hosting keeps the primary product analytics store under owner-operated
  infrastructure, but it creates real operational responsibility.
- PostHog docs state that self-hosting means running the infrastructure,
  choosing URLs, and handling scaling; its open-source self-host docs also warn
  that the open-source deployment is not a managed production service and
  requires security/ops confidence.

**Alternatives considered**:

- PostHog Cloud: faster operations and managed infrastructure, but stronger
  third-party egress and data-residency review. Keep as fallback if self-hosted
  operations are rejected.
- Yandex-only: good for web/ad reports but not the right primary product
  workspace for full-funnel activation, cohorts, and safe product identity.
- Custom analytics tables: rejected for daily product analytics because it adds
  reporting, dashboard, retention, replay, and analysis burden.
- No provider/defer: acceptable only if legal/ops gates reject both providers.

## Decision: Use Yandex As Parallel Web/Ad Surface, Not Product Source Of Truth

Yandex Metrica is planned as a parallel all-web-pages measurement and ad
optimization surface after page inventory, masking, sanitization, legal, QA, and
runtime smoke gates pass. Yandex receives page views/goals/events/session
parameters only for approved page classes. Its default offline conversion
subset is limited to `desktop_account_connected` and
`first_value_session_completed`.

**Rationale**:

- Yandex is already live for the `093` public scope and is the natural surface
  for Yandex Direct optimization.
- Yandex offline conversions require a goal and at least one matching
  identifier such as `ClientID`, `UserID`, `yclid`, or `PurchaseId`; this fits
  a small, explicit milestone subset better than broad product-event fan-out.
- Yandex docs warn not to send identifying information in user/session
  parameters, JavaScript events, UTM tags, URLs, or page titles unless a feature
  explicitly supports that category. This directly supports the forbidden-field
  model in the spec.

**Alternatives considered**:

- Send every activation event to Yandex: rejected as unnecessary product detail
  fan-out.
- Send CRM/customer data to Yandex: rejected for this slice because it would
  introduce names/emails/phones/CRM identifiers and separate legal risk.
- Keep Yandex public-only forever: rejected for product direction, but all-pages
  expansion remains gated by page inventory and masking proof.

## Decision: Prefer Server-Mediated Product Event Delivery First

The first implementation design should default to server-mediated product event
delivery for product milestones. Direct desktop provider SDK/API delivery is
allowed only as a separate high-risk route when legal, security, QA,
forbidden-field, retry, failure, and one-time user acceptance evidence all pass.

**Rationale**:

- Server mediation is easier to audit, redact, retry, and disable centrally.
- Desktop direct delivery increases egress surfaces and makes forbidden-field
  proof harder.
- The user wants one low-friction approval, so any direct desktop egress must be
  explicitly covered by that same approved telemetry package.

**Alternatives considered**:

- Direct desktop to PostHog/Yandex by default: deferred until the direct route
  has exact safe identifiers, payloads, retries, and legal copy.
- Desktop-only local buffer with no provider route: too weak for activation
  analytics unless provider gates fail.

## Decision: Use Stable Server-Issued Pseudonymous User Identity

PostHog product analytics uses a stable server-issued pseudonymous user
identity. Workspace/account/device context may appear only as safe pseudonymous
metadata dimensions. Raw user IDs, account IDs, workspace IDs, names, emails,
device names, local paths, meeting IDs, and content-bearing identifiers are
forbidden.

**Rationale**:

- PostHog identified events are appropriate for logged-in users and activation
  cohorts, but raw personal identifiers are unnecessary.
- Primary "first" milestones must be counted once per person-level pseudonymous
  identity, not once per device/workspace.
- A server-owned namespace gives GRAF a migration path if the analytics provider
  changes.

**Alternatives considered**:

- Raw database IDs: rejected as sensitive and provider-coupling.
- Email/name as `distinct_id`: rejected as identifying information.
- Device ID only: rejected because it double-counts multi-device users.
- Workspace ID only: rejected because it blurs B2C/B2B and multi-workspace use.

## Decision: Use Server-Owned Attribution Bridge

Campaign/source attribution uses `graf_attribution_id` and/or an expiring bridge
token to connect approved public campaign context, Yandex identifiers when
available, PostHog anonymous session, download intent, login/signup, account
connection, and later activation.

**Rationale**:

- Installer download does not prove app open or account connection.
- `desktop_first_opened` should be counted even without campaign linkage, but
  campaign-linked first open is reliable only with a bridge token or
  authenticated handoff.
- `desktop_account_connected` is the first reliable campaign-linked product
  milestone by default.

**Alternatives considered**:

- Try to infer attribution from IP/user agent/time: rejected as unreliable and
  privacy-risky.
- Persist raw Yandex ClientID or `yclid` everywhere: rejected; use only in
  bounded bridge records where allowed.

## Decision: One Low-Friction Mandatory Product Telemetry Gate

Normal desktop app, cabinet, and authenticated product use require one clear
personal acceptance of Terms, Privacy/Personal Data processing documents, and
the bounded product telemetry package. The package must disclose providers,
purposes, event classes, replay boundaries, retention/deletion limits, and any
approved direct desktop provider egress.

**Rationale**:

- The product direction is minimum prompts and maximum lawful analytics.
- A single explicit gate is easier for users than repeated prompts.
- Hidden or unlimited collection is rejected; the accepted package must remain
  bounded to the approved contract.

**Alternatives considered**:

- Optional product analytics opt-out while still using normal product: rejected
  by clarify decision.
- Workspace/admin accepting secretly for users: rejected by clarify decision.
- Dark-pattern acceptance or implied consent: rejected by product gates and
  legal risk.

## Decision: Staged Replay Policy, Not Full Replay By Faith

PostHog Session Replay, Yandex Webvisor, click maps, scroll maps, and form
analytics are enabled only for page classes that pass masking-by-default,
URL/title/referrer sanitization, private DOM hiding, input suppression, QA
evidence, and legal review. If a page class is safe for page views/events but
not safe for replay, safe page views/events may proceed while replay/maps/forms
are disabled and disclosed.

**Rationale**:

- PostHog states masked replay data is not sent over the network when browser/
  app-side masking controls apply.
- Yandex docs say field recognition is not guaranteed and recommend CSS classes
  to guarantee disabling field recording.
- Yandex Webvisor supports `ym-disable-keys` and `ym-hide-content`, but the
  product still must prove no private DOM/text/URL/title/referrer leaks.
- This staged model keeps the project practical without allowing risky real-user
  best-effort replay.

**Alternatives considered**:

- Full replay everywhere or block the whole rollout: rejected as too expensive
  and unnecessary for safe page views/events.
- Best-effort replay on real users: rejected.
- No replay anywhere: rejected because funnel-to-replay is a primary product
  investigation requirement.

## Decision: Retention Starts From A 90-Day Minimum Baseline

Every analytics category receives a retention/deletion statement. The baseline
minimum is 90 days unless a later legal/security gate requires a shorter
category. Replay/Webvisor, bridge records, raw product events, offline
conversions, provider-held aggregates, and exported dashboards must be described
separately.

**Rationale**:

- 90 days is long enough for acquisition-to-activation review and early cohort
  analysis while avoiding indefinite default storage.
- Provider records and exported reports cannot be described as universally
  deleted by GRAF.

**Alternatives considered**:

- 24 months: rejected as too broad for first rollout.
- Shorter than 90 days for everything: may be required for sensitive replay, but
  would weaken activation/cohort analysis if applied globally.

## Decision: Provider Failure Does Not Block Product Workflows

PostHog/Yandex unavailability, script blocking, SDK failure, browser blocking,
or network loss must not block normal product workflows after the telemetry gate
has been accepted. Bounded retry/buffering is allowed for approved events, and
unrecovered loss is shown as a measurement gap.

**Rationale**:

- Analytics is not capture, upload, playback, or result access.
- Provider failure must not reduce trust in the product.
- Measurement caveats are more honest than silent overcount/undercount.

**Alternatives considered**:

- Block product workflows until analytics sends: rejected.
- Expand collection to compensate for gaps: rejected.

## Decision: Count Internal/Support/Smoke/Test Activity By Default

Dashboards and campaign reports count internal, support, smoke, and test
activity by default. Reports must disclose this caveat. Exclusion or labeling is
a separate future feature.

**Rationale**:

- The user explicitly rejected extra complexity to classify "us".
- Counting everyone keeps initial implementation simpler and avoids brittle
  identity heuristics.

**Alternatives considered**:

- IP/email/domain filtering: rejected for this feature because it complicates
  identity and can be wrong.
- Hidden filtering: rejected because reports need truthful interpretation.

## Decision: Runtime Smoke Must Prove Actual Propagation

Future rollout evidence must verify host env or secret source, composed service
config, live container env, rendered HTML/JS, approved page classes, excluded or
replay-disabled unsafe classes, provider script reachability, and provider
dashboard/goal visibility.

**Rationale**:

- Feature `093` found a real production bug where host `.env` contained values
  but Docker Compose did not pass them into `rec-api`.
- For analytics, rendered-page and provider-dashboard proof matter more than
  local configuration alone.

**Alternatives considered**:

- Host `.env` screenshots/logs only: rejected.
- Provider dashboard proof only: rejected because it cannot prove scope
  exclusions or runtime source-of-truth.
