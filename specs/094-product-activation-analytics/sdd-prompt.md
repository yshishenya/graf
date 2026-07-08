# SDD Prompt: Product Activation Analytics

Use this prompt to start the future Spec Kit/SDD flow for feature
`094-product-activation-analytics`.

```text
We need to design product activation analytics for GRAF as a separate Phase 2
feature after `093-public-landing-analytics`.

Current context:

- Feature 093 completed public landing analytics only.
- Public analytics is scoped only to `/` and `/download`.
- Current public analytics provider is Yandex Metrica, disabled by default.
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
- Paid campaign launch for 093 remains blocked until legal review, live Yandex
  setup, dashboard access, and provider smoke are separately approved.

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

Decisions required before implementation:

1. Provider:
   - Compare self-hosted PostHog, PostHog cloud, Yandex-only, another provider,
     and deferral/no-provider.
   - Decide hosting, data residency, retention, deletion participation,
     dashboards, egress, and cost/operations.

2. Identity:
   - Decide whether campaign attribution can link to authenticated/product
     behavior.
   - Consider provider pseudonymous ID, server-issued hashed ID, or expiring
     campaign/session bridge token.
   - Reject raw email, full name, organization/company name, workspace name,
     raw account ID, device name, local paths, OAuth tokens, provider tokens,
     meeting IDs, calendar IDs, and any content-bearing identifiers.

3. Consent / notice / policy:
   - Decide if product analytics is controlled by public consent, separate
     product telemetry notice, first-run desktop notice, workspace policy,
     admin setting, or some combination.
   - Define opt-out and how future events stop after consent/policy changes.

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
   - Acquisition source to activation funnel.
   - Installer download vs first app open.
   - Account connected.
   - Auto-record enabled.
   - First recording completed.
   - First result viewed.
   - First value session completed.
   - Drop-off by safe dimensions only.
   - Internal/test-user filtering.

8. Rollout gates:
   - legal review;
   - operator notice / privacy copy review;
   - provider decision approval;
   - identity and consent approval;
   - test/internal user filtering;
   - provider failure handling;
   - local and production smoke plan;
   - no live IDs or secrets in git;
   - campaign interpretation caveats.

Relevant files to read first:

- `specs/093-public-landing-analytics/spec.md`
- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`
- `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- `specs/093-public-landing-analytics/validation/implementation-evidence.md`
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
