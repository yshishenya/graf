# Product Analytics Yandex Runbook

Feature: `096-product-analytics-provider-rollout`

Status: `implementation_validated_review_remediated`

This runbook is safe to commit. It contains no live Yandex counter ID, OAuth
token, ClientID, Yclid, cookie, visitor identifier, raw CSV row, screenshot,
payload, account data, signed URL, or private local path.

## Purpose

Yandex Metrica remains the external web/ad attribution surface. It is parallel
to PostHog, not the primary product analytics workspace.

096 preserves the 093 public scope and prepares controlled expansion:

- public `/` and `/download` stay approved;
- the existing production counter is reused as the expandable surface;
- every other page class is controlled by inventory state;
- live offline conversions are limited to exactly two product milestones;
- Webvisor/maps/forms remain blocked until separate proof exists;
- paid campaign launch remains blocked separately.

## Counter Strategy

Default strategy: reuse the existing 093 production counter.

Reason:

- preserves acquisition and Yandex Direct attribution continuity;
- avoids splitting public campaign and product conversion reporting;
- supports live offline conversion linkage through one approved counter.

A separate product counter may be introduced only if a later review proves the
existing counter cannot safely support attribution, reporting, or page-class
controls.

Committed evidence must never contain the live counter ID. Evidence may say:

- counter present: yes/no;
- strategy: `reuse_093_production_counter`;
- public baseline: preserved/blocked;
- all-pages expansion: inventory-gated;
- offline conversion readiness: pass/blocked.

## Page Scope

Approved baseline:

| Page Class | Route Examples | Yandex State |
| --- | --- | --- |
| `public_landing` | `/` | approved baseline from 093 |
| `public_download` | `/download` | approved baseline from 093 |

All other current and future browser-rendered pages require inventory state
before Yandex collection:

- `approved_page_view_event`;
- `blocked`;
- `replay_unavailable`.

Future pages default to `blocked` for Yandex until added to the inventory.

Every non-public page approval must record:

- page class;
- allowed event/page fields;
- URL/title/referrer sanitization status;
- forbidden-field review status;
- legal status;
- QA status;
- dashboard purpose;
- rollback behavior.

## Blocked By Default

These classes must not receive Yandex collection by default:

- auth callback;
- admin;
- meeting/result/detail;
- upload;
- deletion;
- embedded desktop webview;
- any page with credential-bearing URL/query/title/referrer risk;
- any future page missing inventory.

## Webvisor, Maps, And Forms

PostHog autocapture approval does not approve Yandex Webvisor, click map, scroll
map, or form analytics.

Each of these needs page-class proof:

- URL/title/referrer sanitization;
- forbidden-field review;
- private DOM review;
- form/input masking;
- legal status;
- QA status;
- dashboard caveat;
- rollback behavior.

## Offline Conversions

Live upload is in scope only for:

- `desktop_account_connected`;
- `first_value_session_completed`.

No other product activation event may be uploaded to Yandex in 096.

Each row must have:

- approved event name;
- conversion datetime;
- one supported identity source: `UserId`, `ClientId`, or `Yclid`;
- dedupe key;
- batch metadata;
- retry state;
- provider status without raw identifiers in evidence.

Evidence must never include raw UserId, ClientID, Yclid, cookies, OAuth token,
or CSV rows.

Identity-source rule:

- `UserId` may be used only when the same GRAF pseudonymous user ID was sent to
  Yandex during an eligible Yandex-counted browser session with `setUserID` and
  `userParams`.
- `ClientId` may be used only when runtime code has a real Yandex `ClientID`
  resolver for that user/session. A boolean `yandex_client_id_present` flag is
  not enough to upload the GRAF pseudonymous user ID as `ClientId`.
- `Yclid` may be used only when runtime attribution captured a real click ID
  from Yandex Direct. The raw value must stay out of git, logs, screenshots,
  and evidence.
- If none of these sources is proven, the offline conversion must remain
  blocked or queued as not reliably attributable.

Implementation note: rendered product pages can bind the pseudonymous Yandex
`UserId` only on inventory-approved Yandex pages. Public `/` and `/download`
continue to use the 093 consent-controlled public Yandex path; product Yandex
initialization must not bypass that consent path.

Official Yandex docs behind this rule:

- Offline conversion import requires at least one of `ClientID`, `UserID`,
  `yclid`, or `PurchaseId`; otherwise the conversion is not attributed to a
  session: https://yandex.com/dev/metrika/en/management/offline-conv
- `setUserID` links custom IDs to `ClientID` only for sessions where the method
  was called: https://yandex.com/support/metrica/en/objects/set-user-id
- `userParams` can pass `UserID` as a custom user parameter:
  https://yandex.com/support/metrica/en/objects/user-params

Duplicate protection:

- every row has a deterministic metadata-only dedupe key;
- retries reuse the dedupe key;
- duplicate evidence records only pass/fail/status, never raw identity values.

Attribution caveat:

- live upload can improve Yandex reporting, but attribution windows and already
  uploaded records are provider-controlled;
- 096 does not approve paid campaign launch.

## OAuth Secret Handling

The OAuth token is supplied only through a runtime secret file. The runbook and
evidence may record:

- secret file configured: yes/no;
- token readable by runtime: yes/no;
- token value redacted: always;
- owner role;
- rotation note;
- smoke status.

Token values must not be printed in logs, examples, dashboards, issue comments,
or implementation evidence.

Rotation:

1. Issue a replacement token outside git.
2. Replace the runtime secret file.
3. Restart or reload only the service that needs offline upload.
4. Run provider smoke.
5. Record redacted status only.

## Retention And Deletion Caveats

Yandex-held reports, aggregates, attribution history, and uploaded offline
conversion records are not automatically erased by a GRAF user deletion action.

User-facing or operator-facing deletion language must distinguish:

- GRAF-controlled data;
- Yandex provider data;
- Yandex aggregate reports;
- already uploaded offline conversion records;
- exported dashboards or reports.

## Dashboard Evidence

Minimum metadata-only evidence:

- sources by source/medium/campaign report exists or blocked;
- public landing to download funnel status;
- Yandex Direct linkage status;
- offline conversion report status for the two approved names;
- page-class scope report status;
- Webvisor/maps/forms availability status;
- retention/deletion caveat status;
- campaign caveat and legal blocker status.

Forbidden dashboard evidence:

- screenshots with visitor/account rows;
- live counter IDs;
- raw click IDs;
- raw ClientID/Yclid/UserId values;
- raw upload rows;
- OAuth tokens.

## Rollback

Rollback must disable:

- all-pages expansion;
- offline conversion upload;
- Webvisor/maps/forms;
- provider validation mode;
- runtime counter injection for unapproved pages.

Expected product impact: measurement gap only.

Rollback restoration requires provider smoke and dashboard caveat update. It
does not approve paid campaign launch.

## Validation Commands

Implementation evidence should record pass/fail summaries for:

```sh
infra/scripts/run-product-analytics-provider-smoke.sh
infra/scripts/validate-product-analytics-provider-pages.sh
infra/scripts/rollback-product-analytics-providers.sh
infra/scripts/cd-remote.sh --dry-run
```

Production deploy execute and paid campaign launch require separate explicit
approval.
