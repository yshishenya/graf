# Contract: Analytics Provider Setup

**Feature**: 093-public-landing-analytics

This contract describes external dashboard configuration required before paid
campaign launch. Do not commit live account identifiers or screenshots with
visitor/account data.

## Yandex Metrica

Production closeout status:

- Counter, domain restriction, Webvisor/scroll/form settings, dashboard access,
  and six JavaScript-event goals are configured for the approved public scope.
- Production provider smoke passed for `/` and `/download`.
- The runtime counter ID is intentionally not committed in this contract.

Required setup:

- Create or select a Metrica counter for the production public site. Done for
  the 093 public scope.
- Configure the production domain used by GRAF. Done for `rec.2brain.pro`.
- Enable Session Replay, scroll map, and form analysis only if public replay is
  approved for `/` and `/download`. Done with consent/runtime gating preserved
  in the browser controller.
- Link the Metrica counter to Yandex Direct campaigns before campaign launch.
- Configure JavaScript event goals matching the public event catalog. Done for
  the six public event names below.

Goals:

| Goal | Event | Priority |
| --- | --- | --- |
| `landing_view` | `public_landing_viewed` | diagnostic |
| `landing_engaged` | `public_landing_section_seen` | secondary |
| `landing_cta_click` | `public_landing_cta_clicked` | secondary |
| `download_page_view` | `public_download_viewed` | secondary |
| `installer_download_click` | `public_installer_download_clicked` | primary |
| `login_intent_click` | `public_login_intent_clicked` | secondary |

Dashboard requirements:

- Sources summary by source/medium/campaign.
- UTM tags report.
- Yandex Direct report when campaigns are linked.
- Funnel or goal report from landing view to installer download click.
- Session Replay/scroll map review limited to public pages.

Runtime environment:

- `TWOBRAIN_PUBLIC_ANALYTICS_ENABLED=false` remains the committed default.
- `TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID` is a runtime-only numeric
  counter ID; do not commit a live ID.
- `TWOBRAIN_PUBLIC_ANALYTICS_VALIDATION_MODE=disabled` is the committed
  production example default. Use `render_only` only for local/test rendering
  validation and `provider_smoke` only with explicit campaign/release approval.
- `TWOBRAIN_PUBLIC_ANALYTICS_REPLAY_ENABLED=false` remains the committed
  default until replay scope and consent are approved.
- `TWOBRAIN_PUBLIC_ANALYTICS_CONSENT_COPY_VERSION` must change when the
  Russian consent copy materially changes.
- Production runtime may set the enabled flag, numeric Yandex counter ID, and
  replay flag externally after approval. Closeout evidence must verify the live
  container environment and rendered pages, not only host-side `.env` files.

Provider failure and duplicate-init handling:

- Blocking the Yandex tag must not break navigation, CTA clicks, installer
  download, login intent, or legal-page access.
- Provider script load failure is recorded as a measurement caveat; it is not
  shown as a user-facing error.
- The browser controller must not append duplicate Yandex provider scripts for
  repeated consent callbacks or multiple tracked actions.
- Duplicate event prevention is handled inside the page controller and should
  be verified before launch.

## Google Deferred Scope

GA4, Google Analytics, Google Ads tags, Google Tag Manager, and Google
conversion import are not part of Phase 1. They may be reconsidered only in a
later legal-approved feature slice that updates privacy/cookie documents,
cross-border transfer evidence, consent behavior, provider setup, and
validation tasks.

## Shared Campaign Readiness

Before paid traffic:

- UTM naming canon is approved.
- Yandex counter ID is configured only in runtime environment/secrets
  management. Ad account references, if any, must also stay out of git.
- Consent banner text is approved in Russian.
- Public privacy, cookie, terms, analytics-consent, and cookie-settings links
  are available from the consent UI and footer.
- Personal-data operator notice status is reviewed before public campaign
  launch.
- Foreign analytics providers remain disabled unless a later legal-approved
  slice completes cross-border transfer and consent evidence.
- Disabled, unknown, accept-all, necessary-only, customized, revoked, and
  provider-blocked states are validated.
- Primary and secondary conversions are visible in Yandex debug or reporting
  views.
- Dashboard owners have access.
- Known caveats are documented: consent undercount, blocked tags, ad-platform
  attribution windows, duplicate clicks, direct traffic, and download not
  proving activation.

Completed before 093 closeout:

- Public Yandex counter and goals configured.
- Dashboard access verified.
- Production deploy and provider smoke passed for `/` and `/download`.
- Runtime propagation verified from server env into live `rec-api` and rendered
  public pages.
- Negative scope verified for `/login`.

Still required before paid campaign launch:

- Legal/campaign-readiness approval by the project owner or reviewer.
- Personal-data/operator notice status decision.
- Yandex Direct campaign/linking decision when paid traffic is started.
- Campaign naming canon and interpretation caveats acknowledged by the growth
  owner.

Closeout note template:

```yaml
feature: 093-public-landing-analytics
analytics_runtime:
  enabled: false
  yandex_counter_id: runtime_only_redacted
  validation_mode: disabled
  replay_enabled: false
legal_readiness:
  owner: not_assigned
  review_status: not_started
  operator_notice_status: not_checked
  foreign_provider_status: yandex_only_phase1_google_deferred
campaign_readiness:
  decision: blocked
  blocker_summary:
    - legal_reviewer_not_approved
    - paid_campaign_readiness_not_approved
```

## Legal Readiness Evidence

Record a metadata-only legal readiness entry before campaign launch:

- `owner`: person or role responsible for the review.
- `review_status`: `not_started`, `in_review`, `approved`, or `blocked`.
- `reviewed_at`: date or `not_reviewed`.
- `operator_notice_status`: `not_checked`, `not_required_by_reviewer`,
  `submitted`, `updated`, or `blocked`.
- `foreign_provider_status`: `not_enabled` for Phase 1.
- `blockers`: short non-secret summary, or `none`.
- `campaign_decision`: `blocked` or `ready_for_approved_campaign_smoke`.

The evidence is an implementation/campaign-readiness record, not legal advice.
If reviewer approval is absent or blocked, paid campaign launch remains
blocked.

## Evidence Safety

Allowed evidence:

- Goal names.
- Event names.
- Pass/fail state.
- Redacted provider names.
- Timestamp.
- Environment name.
- High-level dashboard availability.

Forbidden evidence:

- Live counter IDs.
- Ad account IDs.
- Conversion IDs.
- Cookies.
- Client IDs.
- Visitor IDs.
- Email, account, or organization identifiers.
- Screenshots with raw visitor or account data.
- Raw network payload dumps.
