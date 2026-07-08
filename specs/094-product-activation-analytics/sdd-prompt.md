# SDD Prompt: Product Activation Analytics

Use this prompt to start the future Spec Kit/SDD flow for feature
`094-product-activation-analytics`.

```text
We need to design product activation analytics for GRAF as a separate Phase 2
feature after `093-public-landing-analytics`.

Current context:

- Feature 093 completed public landing analytics only.
- Public analytics is scoped only to `/` and `/download`.
- Current public analytics provider is Yandex Metrica. Committed defaults stay
  disabled, while approved production runtime now enables the public counter
  through external env configuration.
- Public web events include:
  - `public_landing_viewed`
  - `public_landing_section_seen`
  - `public_landing_cta_clicked`
  - `public_download_viewed`
  - `public_installer_download_clicked`
  - `public_login_intent_clicked`
- Primary web conversion is installer download intent:
  `public_installer_download_clicked`.
- Public analytics is consent-first through self-hosted CookieConsent v3.1.0.
- Webvisor/replay is public-page-only and gated by `behavior_replay` consent.
- Google/GA4/GTM are explicitly deferred.
- PostHog/product analytics code is explicitly absent from Phase 1.
- Live Yandex counter/goals, dashboard access, and production provider smoke
  are complete for the 093 public scope. Paid campaign launch still remains
  blocked until legal and campaign-readiness approval.

093 post-deploy facts to preserve:

- Production public analytics is live only for `/` and `/download`.
- The live production counter and six Yandex JS-event goals were configured for
  the public scope.
- Production smoke verified container env, health endpoints, rendered HTML
  analytics config, rendered public event catalog, Yandex script reachability,
  and absence of the public analytics dispatcher on `/login`.
- A real deployment bug was found and fixed: production `.env` contained the
  analytics values, but `docker-compose.yml` did not pass those runtime values
  into `rec-api`. Future analytics rollout evidence must verify host env or
  secret source, composed service config, live container env, rendered
  HTML/JS, allowed page classes, blocked page classes, provider script
  reachability, and provider dashboard/goal visibility.
- Live counter IDs and provider identifiers are runtime/provider
  configuration. Do not hard-code live provider IDs, API keys, tokens, signed
  URLs, credentials, or private evidence in source, tests, specs, or release
  notes.

Important boundary:

Do not implement product analytics yet. This feature is a high-risk SDD/spec
slice first. It must go through clarify, plan, checklist, analyze, tasks, and
only then implementation approval.

The new problem:

Public analytics can tell us that someone clicked download, but it cannot tell
us whether the person actually activated the product. We need product analytics
for the app/cabinet/desktop flow so a product owner can understand:

- first desktop app open;
- account connection;
- auto-record enabled;
- first recording completed;
- first result viewed;
- first value session completed;
- where users drop off after installation;
- which campaign/source produces real activation, not only download intent.

Candidate activation funnel:

public_installer_download_clicked
-> desktop_first_opened
-> desktop_account_connected
-> desktop_autorecord_enabled
-> first_recording_completed
-> first_result_viewed
-> first_value_session_completed

Target analytics model:

Use two analytics systems in parallel, but with explicit role separation and no
manual data-moving workflow as the normal operating model.

Final product direction to preserve in SDD:

The desired operating model is "maximum useful measurement in two systems,
one primary daily workspace." This means GRAF should intentionally run both
PostHog and Yandex Metrica after the future high-risk approval, but each system
has a clear job:

- PostHog answers product questions: which source produced a real activated
  user, where onboarding drops off, which users reached first value, which
  cohorts retain, which product steps need work, and which session recordings
  explain the drop-off inside the primary analytics workspace.
- Yandex answers web/ad/replay questions: how traffic behaves across all web
  pages, what Yandex Direct can optimize against, what users did in Webvisor,
  and which approved activation milestones should be fed back to advertising.
- The product owner should not need routine CSV exports, spreadsheet joins,
  custom ETL, or two dashboards to understand the main user journey. The main
  journey lives in PostHog. Yandex is a parallel advertising and replay surface.

When the user says "enable everything possible", interpret it as:

- enable all approved PostHog product analytics capabilities needed for the
  full funnel, cohorts, retention, drop-off, source/campaign segmentation, and
  first-value analysis;
- enable PostHog Session Replay for approved browser-rendered web/product pages
  so funnel steps and drop-offs can open matching recordings inside PostHog;
- enable Yandex Metrica on all approved browser-rendered web pages, not only
  public pages;
- enable Yandex goals/events, safe page categories, safe session/user
  parameters, click maps, scroll maps, form analytics, and Webvisor/session
  replay everywhere after the required masking/sanitization gates pass;
- automate any approved Yandex offline conversion feedback instead of relying
  on manual exports;
- do not treat "everything possible" as permission to send forbidden data,
  unmasked replay, raw identifiers, meeting content, secrets, or ad-retargeting
  pixels without a separate future approval.

The SDD must not leave the provider model vague. It must produce a concrete
measurement-routing design with these default positions:

| Area | Default destination | Why |
| --- | --- | --- |
| Public page views and safe public events | PostHog + Yandex | PostHog needs acquisition context for the full funnel; Yandex needs web/ad measurement. |
| Public session replay | PostHog + Yandex | PostHog supports funnel-to-replay inside the primary workspace; Yandex Webvisor supports web/ad behavior review. |
| Auth/cabinet/product web page views | PostHog + Yandex | PostHog needs product journey context; Yandex is enabled on all web pages after sanitization. |
| Auth/cabinet/product session replay | PostHog + Yandex | PostHog keeps product funnel review convenient; Yandex target is full Webvisor everywhere after masking-by-default and legal/QA gates. |
| Desktop-native product milestones | PostHog | PostHog is the product source of truth. |
| Approved activation milestones for ad optimization | Yandex offline conversions | Only approved milestone subset, sent automatically with safe identifiers. |
| Retention/cohort/drop-off/product dashboards | PostHog | PostHog is the daily product analytics workspace. |
| Yandex Direct optimization and ad reports | Yandex | Yandex remains the advertising optimization surface. |

Recommended attribution model:

Use a server-owned attribution bridge. The default bridge identifier should be a
safe `graf_attribution_id` and/or expiring bridge token created from the first
approved web touch. It may connect:

- UTM/openstat campaign context;
- `yclid`;
- Yandex ClientID when available and legally allowed;
- PostHog anonymous ID;
- public session and landing/download events;
- installer download click;
- login/signup/auth callback;
- account connection;
- later product activation milestones.

The bridge must not expose raw email, phone, names, organization/company names,
workspace names, account IDs, user IDs, meeting IDs, calendar IDs, device names,
local paths, object keys, signed URLs, OAuth/provider tokens, passcodes, meeting
links, transcript text, audio, or other content-bearing values.

Attribution reliability must be explicit:

- Count `desktop_first_opened` for product adoption even when it cannot be
  tied to a campaign.
- Treat campaign-linked `desktop_first_opened` as reliable only when a bridge
  token, authenticated handoff, or equivalent safe proof exists.
- Treat `desktop_account_connected` as the first reliable campaign-linked
  product milestone unless the future implementation proves a safer earlier
  handoff.
- Do not promise 100% attribution from installer download to first desktop open
  when the installer package itself cannot carry safe campaign context.

1. PostHog is the primary full-funnel analytics workspace.
   - It must be the daily place where the product owner sees the whole path:
     campaign/source -> public landing/download intent -> desktop first open ->
     account connection -> auto-record enablement -> first recording -> first
     result view -> first value.
   - It should receive all approved public acquisition events and all approved
     product activation events needed for the full journey.
   - It is the source of truth for onboarding, activation, retention, cohorts,
     drop-off, and first-value analysis.
   - It should include PostHog Session Replay for approved browser-rendered
     public, auth, cabinet, and product web pages so the product owner can move
     from a funnel/drop-off/cohort segment directly into matching recordings
     without opening Yandex or doing manual ID matching.
   - PostHog Session Replay must use masking-by-default, URL/title/referrer
     sanitization, private DOM hiding, input suppression, forbidden-field
     controls, QA evidence, and legal review. This decision does not authorize
     desktop-native screen/audio replay.

2. Yandex Metrica is the parallel all-web-pages measurement and advertising
   optimization workspace.
   - It should be enabled on every approved browser-rendered web page, not only
     `/` and `/download`: public, download, legal, auth, cabinet, and
     authenticated product web surfaces.
   - It should receive the maximum approved Yandex measurement for those pages:
     page views, traffic sources, UTM/openstat where relevant, safe goals,
     safe custom events, safe page categories, safe funnel steps,
     click/scroll/form-map capabilities where legally and technically safe, and
     Webvisor/session replay everywhere after the mandatory replay/masking gate
     passes for each page class.
   - It remains the natural place for Yandex Direct, advertising reports,
     public and authenticated web behavior, and optional offline-conversion
     feedback.
   - It is not the primary source of truth for product activation; PostHog
     remains the full-funnel product workspace.
   - "All pages" does not mean raw page data may be sent blindly. The SDD must
     define route/page-title/referrer sanitization before the Yandex tag is
     allowed on authenticated, cabinet, meeting, upload, playback, deletion,
     admin, or embedded desktop web surfaces.
   - The target Webvisor/session replay policy is full replay everywhere on all
     approved browser-rendered web pages. If a page class cannot be made safe
     through masking-by-default, URL/title/referrer sanitization, form/input
     suppression, private DOM hiding, and QA/legal evidence, the SDD must treat
     that as a launch blocker or require route/DOM/product redesign rather than
     silently excluding the page from replay.

3. Approved product milestones may be sent back to Yandex as offline
   conversions only when useful for advertising optimization.
   - Candidate offline conversions:
     `desktop_first_opened`, `desktop_account_connected`,
     `first_recording_completed`, `first_result_viewed`,
     `first_value_session_completed`.
   - The SDD must decide the exact subset. Do not send every product event to
     Yandex by default.
   - Each exported milestone must have an allowed identifier strategy, allowed
     fields, retention/deletion statement, and advertising purpose.

4. "Enable everything possible" means maximum approved measurement inside these
   boundaries.
   - Do enable all useful goals, UTM/source capture, safe funnel events, and
     approved dashboard dimensions.
   - Do enable Yandex Metrica across all approved web pages after the page
     inventory, legal gate, and sanitization controls pass.
   - Do enable Yandex Webvisor/session replay across all approved web pages
     after masking-by-default, sanitization, QA evidence, and legal review pass.
   - Do not enable unlimited event fan-out, unmasked product/cabinet/meeting
     replay, ad retargeting pixels, raw email/name/workspace/account IDs,
     meeting titles, participants, audio, transcripts, calendar text, local
     paths, tokens, signed URLs, passcodes, secrets, or other forbidden fields.
   - Do not rely on Yandex automatic collection when route names, page titles,
     referrers, search strings, form fields, DOM text, or replay content may
     contain private product data. Redesign the route/title/DOM output, mask it,
     or block that Yandex capability for the page class.
   - Do not make a future PostHog-Yandex roadmap connector a launch dependency.
   - Do not require routine CSV exports, manual joins, spreadsheet reporting, or
     custom ETL as the daily analytics process.

Mandatory SDD outputs:

The future SDD must create these artifacts before tasks or implementation:

1. Parallel measurement matrix.
   - One row per event/page milestone.
   - Columns: event name, owner, surface, PostHog yes/no, Yandex yes/no,
     Yandex mode (tag event, goal, user/session parameter, offline conversion,
     replay-only, no data), reason, allowed fields, forbidden fields, identity,
     retention/deletion truth, dashboard owner, QA evidence.

2. Yandex all-pages inventory.
   - One row per page class: public landing, download, legal, login/signup,
     auth callback, cabinet home, onboarding, settings, recording list,
     meeting/result detail, upload, playback, deletion, admin, embedded desktop
     webview, error pages.
   - Columns: Yandex tag allowed, page view allowed, goals/events allowed,
     click map allowed, scroll map allowed, form analytics allowed,
     Webvisor/session replay allowed, masking rules, URL/title/referrer rules,
     DOM/private text rules, launch status, blocker if unsafe.

3. Replay masking contract.
   - Applies to both PostHog Session Replay and Yandex Webvisor/session replay.
   - Default rule: masking-by-default for authenticated/product pages.
   - All input, textarea, editor, transcript, title, participant, meeting,
     workspace, account, file, local path, token, signed URL, payment/contact,
     calendar, and free-text regions must be hidden or suppressed before
     replay is allowed.
   - Only explicitly safe neutral UI regions may remain visible.
   - If a page cannot meet the contract, launch is blocked or the page must be
     redesigned.

4. Identity and attribution contract.
   - Use the server-owned attribution bridge as the default model.
   - Define how `graf_attribution_id`, Yandex ClientID, `yclid`, PostHog
     anonymous ID, provider pseudonymous ID, server-issued hashed ID, and/or
     expiring bridge token are created, stored, joined, expired, rotated, and
     deleted.
   - Raw email, names, workspace names, raw account/workspace/user/meeting IDs,
     device names, local paths, tokens, object keys, signed URLs, meeting links,
     calendar IDs, and content-bearing identifiers are forbidden.
   - Explain how public campaign context joins to product activation without
     exposing raw identity.
   - Explain attribution reliability for every milestone, especially the gap
     between `public_installer_download_clicked` and `desktop_first_opened`.

5. Legal and consent gate.
   - Same B2B/B2C path.
   - Normal product use is blocked until the user accepts the required Terms,
     Privacy/Personal Data processing documents, and mandatory bounded product
     telemetry package.
   - The required package includes approved PostHog product analytics and
     masked/sanitized Yandex all-pages measurement/replay.
   - If the user withdraws required consent or refuses updated mandatory terms,
     normal product use stops or is limited to account/legal/export/deletion
     flows.

6. Dashboard map.
   - PostHog dashboards: source/campaign to first value, installer download vs
     first app open, account connected, auto-record enabled, first recording,
     first result viewed, first value, drop-off, retention, cohorts, internal
     traffic exclusion, and funnel-to-session-replay drilldowns.
   - Yandex dashboards: all-web page behavior, Yandex Direct reports, Webvisor,
     click/scroll/form reports where allowed, public goals, authenticated safe
     goals, approved offline conversion feedback.

7. Launch blockers.
   - Missing legal approval.
   - Missing hard telemetry gate copy.
   - Missing provider configuration.
   - Missing proof that runtime env/secret values reach the live analytics
     service container and rendered approved pages.
   - Missing Yandex all-pages inventory.
   - Unsafe URL/title/referrer for any tagged page.
   - Unsafe unmasked DOM/replay region.
   - Forbidden field in any event, parameter, URL, title, or replay payload.
   - Missing internal/test-user filtering.
   - Missing dashboard owner.
   - Missing local and production smoke evidence.
   - Smoke evidence checks only host-side `.env` or local config, without live
     container env and rendered page verification.
   - Any manual export/CSV/spreadsheet process required for normal daily
     analytics.

Decisions required before implementation:

1. Provider:
   - Compare self-hosted PostHog, PostHog cloud, Yandex-only, another provider,
     and deferral/no-provider.
   - Decide hosting, data residency, retention, deletion participation,
     dashboards, egress, and cost/operations.
   - Optimize for one primary analytics workspace where the product owner sees
     the full path from approved public acquisition events to first product
     value without routine manual exports, custom ETL, or switching between
     dashboards.
   - Treat self-hosted PostHog as the preferred primary full-funnel analytics
     home unless research/legal/operations gates reject it.
   - Treat Yandex Metrica as a parallel all-web-pages measurement and
     advertising optimization surface. Do not depend on a future PostHog-Yandex
     roadmap connector. If needed for ad optimization, only approved activation
     milestones may be sent back to Yandex as offline conversions.
   - Define the parallel measurement matrix: for each public and product event,
     state whether it goes to PostHog, Yandex, both, or neither; why; which
     fields are allowed; which identity is used; and which dashboard owns the
     metric.
   - Define the Yandex all-pages inventory: for each browser-rendered page class
     state whether Yandex receives page views, goals/events, session
     parameters, user parameters, Webvisor/session replay, click map, scroll
     map, form analysis, offline conversions, or no data. Include URL/title
     sanitization, DOM masking, identity, retention, deletion, and legal
     evidence for every page class.

2. Identity:
   - Decide whether campaign attribution can link to authenticated/product
     behavior.
   - Consider provider pseudonymous ID, server-issued hashed ID, or expiring
     campaign/session bridge token.
   - Reject raw email, full name, organization/company name, workspace name,
     raw account ID, device name, local paths, OAuth tokens, provider tokens,
     meeting IDs, calendar IDs, and any content-bearing identifiers.

3. Consent / notice / policy:
   - Use the same B2B/workspace and B2C path.
   - Design a hard product-use gate: normal desktop app, cabinet, and
     authenticated product use cannot continue unless the user accepts the
     required Terms, Privacy/Personal Data processing documents, and mandatory
     bounded product telemetry package.
   - The mandatory package must remain limited to approved activation
     analytics and masked/sanitized Yandex Webvisor/session replay. It must not
     include unmasked product/cabinet/meeting replay, ad retargeting pixels, raw
     identities, meeting content, audio, transcripts, calendar text, local
     paths, secrets, signed URLs, or other forbidden fields.
   - Define what happens when a user withdraws required consent or refuses
     updated mandatory terms: future product analytics stops because normal
     product use stops or is limited to account/legal/export/deletion flows.

4. Forbidden data:
   - Never send raw audio, transcript, meeting title, participants, calendar
     event text, meeting links, local file paths, object keys, signed URLs,
     tokens, passcodes, email, names, workspace/account names, or raw IDs.

5. Event contract:
   - Define safe events, owners, surfaces, allowed fields, forbidden fields,
     consent/notice requirement, identity rule, and deletion/reporting truth
     for each event:
     - `desktop_first_opened`
     - `desktop_account_connected`
     - `desktop_autorecord_enabled`
     - `first_recording_completed`
     - `first_result_viewed`
     - `first_value_session_completed`

6. Deletion and reporting truth:
   - Do not promise universal deletion outside GRAF control.
   - Explain aggregate provider reports, exported dashboards, and ad-platform
     imports separately.
   - Preserve the GRAF deletion boundary language.

7. Dashboards:
   - One primary PostHog workspace for acquisition source to activation funnel.
   - Installer download vs first app open.
   - Account connected.
   - Auto-record enabled.
   - First recording completed.
   - First result viewed.
   - First value session completed.
   - Drop-off by safe dimensions only.
   - Internal/test-user filtering.
   - Optional Yandex Metrica/Direct feedback reports for advertising decisions
     only; they must not become the source of truth for product activation.

8. Rollout gates:
   - legal review;
   - required Terms, Privacy/Personal Data processing documents, and operator
     notice review;
   - provider decision approval;
   - identity and hard product telemetry gate approval;
   - test/internal user filtering;
   - provider failure handling;
   - local and production smoke plan that verifies host env/secret source,
     composed service config, live container env, rendered HTML/JS on approved
     pages, expected absence on blocked pages, provider script reachability,
     and provider dashboard/goal visibility;
   - no live IDs or secrets in git;
   - campaign interpretation caveats.

Relevant files to read first:

- `specs/093-public-landing-analytics/spec.md`
- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`
- `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- `specs/093-public-landing-analytics/validation/implementation-evidence.md`
- `infra/docker-compose.yml`
- `apps/server/tests/integration/test_compose_hardening.py`
- `docs/agent-guidance/product-gates.md`
- `docs/agent-guidance/spec-kit-flow.md`
- `.specify/memory/constitution.md`
- `docs/prd-voice-layer-final.md`
- `docs/current-product-status.md`

Expected SDD flow:

$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-taskstoissues

Do not implement until blockers are resolved and implementation is explicitly
approved.
```
