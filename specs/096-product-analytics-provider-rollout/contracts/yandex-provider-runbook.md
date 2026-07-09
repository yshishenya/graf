# Contract: Yandex Provider Runbook

**Feature**: `096-product-analytics-provider-rollout`

This contract defines the Yandex Metrica expansion after 093. It does not commit a live counter ID or OAuth token.

## Counter Strategy

- Reuse the existing production Yandex counter configured in 093.
- Preserve the currently live public scope: `/` and `/download`.
- Use the same counter for expandable all-pages measurement, Yandex Direct attribution continuity, and approved live offline conversions.
- A separate product counter is not the default. It may be introduced only if planning or provider constraints prove the existing counter cannot safely support attribution and page-class controls.

## Yandex Surface Roles

Yandex is for:

- public acquisition reporting;
- Yandex Direct attribution;
- approved safe page views/events;
- approved Webvisor/click map/scroll map/form analytics after proof;
- live offline conversions for two activation milestones.

Yandex is not:

- the primary product analytics workspace;
- a destination for PostHog broad autocapture exports;
- a destination for content-bearing meeting/product data;
- paid campaign launch approval.

## All-Pages Inventory Contract

Every current and future browser-rendered page class must have a Yandex state before collection:

- `approved_page_view_event`
- `blocked`
- `replay_unavailable`

Future pages default to `blocked` for Yandex until added to the inventory.

The inventory must include:

- public landing;
- download;
- legal;
- login/signup;
- auth callback;
- cabinet;
- onboarding;
- settings;
- recording list;
- meeting/result/detail;
- upload;
- playback;
- deletion;
- admin;
- embedded desktop webview;
- error pages;
- future browser-rendered page classes.

## Live Offline Conversion Contract

Live upload is enabled in 096 for exactly:

- `desktop_account_connected`
- `first_value_session_completed`

No other product event may be uploaded to Yandex in 096.

Each upload row must use a Yandex-supported identity key source:

- `UserId`
- `ClientId`
- `Yclid`

The committed evidence must never include raw values for those identifiers.

`UserId` is valid only when the same GRAF pseudonymous user ID was sent to
Yandex on an eligible counted browser page through `setUserID` and
`userParams`. `ClientId` and `Yclid` require real runtime resolver values and
must not be synthesized from the GRAF pseudonymous user ID.

## OAuth And Access Contract

- OAuth token is supplied only through a runtime secret file.
- Token must have sufficient Yandex Metrica API access for offline data upload.
- Token owner and counter access must be validated in provider smoke.
- Token must not be printed in logs, committed evidence, screenshots, or command examples with real values.

## Duplicate And Retry Contract

The implementation must define:

- dedupe key for each offline conversion row;
- upload batch ID;
- retry policy;
- provider status polling or equivalent visibility;
- duplicate-suppression evidence;
- attribution-window caveat.

## Retention And Deletion Caveat Contract

The implementation runbook must document truthful lifecycle behavior for:

- public page/ad reporting data in the reused 093 counter;
- approved offline conversions for `desktop_account_connected` and `first_value_session_completed`;
- Yandex Direct attribution linkage;
- dashboard/report aggregates;
- rollback-disabled future uploads.

The runbook must not promise that a GRAF user deletion action universally erases
Yandex-held aggregates, provider reports, attribution history, or already uploaded
offline conversion records. Evidence may record only metadata such as conversion
names, report names, retention/caveat status, blocker codes, and pass/fail
validation status.

## Webvisor/Map/Form Contract

Yandex Webvisor, click map, scroll map, and form analytics require page-class proof. PostHog autocapture everywhere does not approve Yandex Webvisor or maps.

Meeting/result/detail, admin, auth callback, deletion, upload, and embedded desktop webview remain blocked or replay-unavailable for Yandex until explicit proof exists.

## Dashboard Requirements

Minimum Yandex dashboards:

- sources by source/medium/campaign;
- public landing to download funnel;
- Yandex Direct report when linked;
- offline conversion report for two product milestones;
- page-class scope report;
- Webvisor/map/form availability report;
- retention/deletion caveat report;
- campaign caveat and legal blocker status.

## Rollback Requirements

Rollback must disable:

- all-pages expansion;
- offline conversion upload;
- Webvisor/maps/forms;
- provider validation mode;
- runtime counter injection for unapproved pages.

Rollback expected product impact: measurement gap only.

## Evidence Requirements

Allowed evidence:

- event names;
- goal names;
- redacted counter presence;
- upload pass/fail status;
- status polling result without payload rows;
- dashboard availability status;
- blocker codes.

Forbidden evidence:

- live counter IDs;
- OAuth tokens;
- ClientIDs, Yclids, cookies, visitor IDs;
- raw CSV rows;
- screenshots with visitor/account data;
- raw network payload dumps.
