# Data Model: Public Landing Analytics

**Feature**: 093-public-landing-analytics

This model describes public-page analytics concepts and contracts. Phase 1 does
not add server database tables; runtime event storage belongs to the configured
Yandex Metrica provider.

## Entity: Public Analytics Runtime Configuration

**Purpose**: Non-secret server configuration deciding whether public analytics
is rendered.

**Fields**:

- `enabled`: boolean feature flag.
- `environment_allowed`: true only for production-like environments approved
  for analytics.
- `yandex_metrica_id_present`: true when a runtime Metrica counter ID exists.
- `replay_allowed`: true only when public replay is approved for `/` and
  `/download`.
- `validation_mode`: `disabled`, `render_only`, `provider_smoke`.
- `consent_copy_version`: stable version for consent persistence.

**Validation rules**:

- Disabled if `enabled` is false.
- Disabled if the Yandex Metrica counter ID is absent.
- Disabled in local/test/CI unless validation explicitly requests render-only
  enabled analytics.
- Provider IDs are runtime configuration. Do not commit live IDs or account
  IDs in specs, tests, screenshots, logs, or evidence.

## Entity: Public Analytics Consent Preference

**Purpose**: Browser-local preference that controls non-essential public
analytics.

**Fields**:

- `state`: `unknown`, `accepted_all`, `necessary_only`, `customized`,
  `revoked`.
- `analytics_allowed`: boolean optional category grant.
- `advertising_attribution_allowed`: boolean optional category grant.
- `behavior_replay_allowed`: boolean optional category grant.
- `copy_version`: version of the Russian consent text.
- `decided_at`: browser timestamp.
- `surface`: `/` or `/download`.

**State transitions**:

```text
unknown -> accepted_all
unknown -> necessary_only
unknown -> customized
accepted_all -> revoked
accepted_all -> necessary_only
accepted_all -> customized
necessary_only -> accepted_all
necessary_only -> customized
customized -> accepted_all
customized -> necessary_only
customized -> revoked
revoked -> accepted_all
revoked -> necessary_only
revoked -> customized
```

**Validation rules**:

- Stored locally in the visitor's browser only.
- `accepted_all` means all optional Phase 1 categories are allowed.
- `necessary_only` means no Yandex Metrica or replay.
- `customized` loads only the optional categories explicitly granted.
- Must not include email, account ID, user ID, meeting title, transcript,
  audio, local path, object key, token, signed URL, passcode, or private
  content.
- A new `copy_version` may reset the visible consent prompt if copy materially
  changes.

## Entity: Public Campaign Attribution

**Purpose**: Safe campaign data attached to public analytics events.

**Fields**:

- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_id`
- `utm_content`
- `utm_term`
- `referrer_category`: `direct`, `organic`, `referral`, `paid`, `unknown`.
- `landing_path`: `/` or `/download`.
- `normalization_status`: `clean`, `normalized`, `missing`, `unsafe_dropped`.

**Validation rules**:

- Trim leading/trailing whitespace.
- Normalize source and medium to lowercase.
- Drop unsafe values that look like email, phone, token, signed/private link,
  passcode, raw account ID, or private customer/project name.
- Do not invent campaign values for direct or unknown traffic.

## Entity: Public Landing Analytics Event

**Purpose**: One approved public-page action or milestone.

**Fields**:

- `event_name`: one approved event name.
- `page_path`: `/` or `/download`.
- `surface`: `public_landing` or `public_download`.
- `section_id`: stable section identifier, nullable.
- `cta_location`: stable CTA identifier, nullable.
- `target_kind`: `download_page`, `installer_package`, `login`, `section`.
- `consent_state`: current consent state.
- `campaign_attribution`: Public Campaign Attribution.
- `device_class`: provider-derived device class where available.
- `provider_delivery`: `not_configured`, `blocked`, `sent`, `skipped`.

**Approved event names**:

| Event | Meaning | Primary Fields |
| --- | --- | --- |
| `public_landing_viewed` | Public landing rendered for a visitor | page_path, campaign attribution |
| `public_landing_section_seen` | A major landing section became visible | section_id |
| `public_landing_cta_clicked` | A landing CTA was clicked | cta_location, target_kind |
| `public_download_viewed` | Download handoff page rendered | page_path, campaign attribution |
| `public_installer_download_clicked` | Installer link clicked | target_kind |
| `public_login_intent_clicked` | Login link clicked from public pages | cta_location, target_kind |

**Validation rules**:

- No event outside the approved list in Phase 1.
- No visible section text, transcript-like example text, account text, file
  names, installer local paths, provider account IDs, raw cookies, or user
  identifiers in event fields.
- One visitor action emits at most one event per provider for that action.

## Entity: Public Conversion Goal

**Purpose**: Dashboard-owned conversion definition used by Yandex Metrica.

**Fields**:

- `goal_name`
- `priority`: `primary`, `secondary`, `diagnostic`
- `counted_event`
- `allowed_surface`
- `provider_mapping`
- `deduplication_rule`
- `dashboard_owner`
- `reporting_caveat`

**Goal catalog**:

| Goal | Priority | Counted Event | Notes |
| --- | --- | --- | --- |
| `landing_view` | diagnostic | `public_landing_viewed` | Useful denominator, not a conversion |
| `landing_engaged` | secondary | `public_landing_section_seen` | Section reach or qualified scroll |
| `landing_cta_click` | secondary | `public_landing_cta_clicked` | CTA intent from header/hero/final |
| `download_page_view` | secondary | `public_download_viewed` | Handoff reached |
| `installer_download_click` | primary | `public_installer_download_clicked` | Primary web conversion |
| `login_intent_click` | secondary | `public_login_intent_clicked` | Separate path, not installer download |

**Validation rules**:

- Installer download click is web conversion only; it does not prove install,
  login, recording, or product value.
- Provider dashboard names must map unambiguously to the catalog.

## Entity: Analytics Provider Setup

**Purpose**: External dashboard configuration required for campaign launch.

**Fields**:

- `provider`: `yandex_metrica`.
- `account_owner`: external owner responsible for dashboard access.
- `counter_id`: configured outside git.
- `goals_configured`: list of Public Conversion Goals.
- `ad_account_link_state`: `not_linked`, `linked`, `blocked`, `unknown`.
- `replay_state`: `off`, `public_pages_only`, `blocked`.
- `last_smoke_at`: metadata-only timestamp.

**Validation rules**:

- Do not commit live counter IDs, account IDs, conversion IDs, or screenshots
  containing account/visitor identifiers.
- Smoke evidence records pass/fail and goal names only.

## Entity: Phase 2 Activation Event Contract

**Purpose**: Future product analytics milestones that can link campaigns to
real product activation.

**Fields**:

- `event_name`
- `surface`: `desktop`, `web_cabinet`, `server`.
- `safe_fields`
- `identity_rule`
- `consent_or_notice_requirement`
- `forbidden_data`
- `implementation_phase`
- `validation_requirement`

**Required future events**:

| Event | Meaning |
| --- | --- |
| `desktop_first_opened` | Desktop app opened after installation |
| `desktop_account_connected` | Desktop app linked to an authenticated account |
| `desktop_autorecord_enabled` | User enabled policy-allowed autorecord |
| `first_recording_completed` | First recording completed locally/server-side |
| `first_result_viewed` | First processed meeting result opened |
| `first_value_session_completed` | User reached a complete first-value path |

**Validation rules**:

- Phase 2 identity must use a safe hashed or provider pseudonymous identifier.
- Never send email, account name, meeting title, transcript, raw audio, local
  path, object key, token, signed URL, password, passcode, or private meeting
  content.
- Phase 2 requires a separate high-risk spec before implementation.
