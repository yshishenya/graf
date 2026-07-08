# Contract: Analytics Provider Setup

**Feature**: 093-public-landing-analytics

This contract describes external dashboard configuration required before paid
campaign launch. Do not commit live account identifiers or screenshots with
visitor/account data.

## Yandex Metrica

Required setup:

- Create or select a Metrica counter for the production public site.
- Configure the production domain used by GRAF.
- Enable Session Replay, scroll map, and form analysis only if public replay is
  approved for `/` and `/download`.
- Link the Metrica counter to Yandex Direct campaigns before campaign launch.
- Configure JavaScript event goals matching the public event catalog.

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

## Google Deferred Scope

GA4, Google Analytics, Google Ads tags, Google Tag Manager, and Google
conversion import are not part of Phase 1. They may be reconsidered only in a
later legal-approved feature slice that updates privacy/cookie documents,
cross-border transfer evidence, consent behavior, provider setup, and
validation tasks.

## Shared Campaign Readiness

Before paid traffic:

- UTM naming canon is approved.
- Yandex counter ID and ad account references are configured only in runtime
  environment/secrets management.
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
