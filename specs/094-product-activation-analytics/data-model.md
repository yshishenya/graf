# Data Model: Product Activation Analytics

**Feature**: `094-product-activation-analytics`

This is a logical analytics data model. It does not create database tables or
provider schemas by itself.

## ProductActivationEvent

Represents one approved product or public activation milestone.

**Fields**:

- `event_name`: enum. Public events from `093` plus product events:
  `desktop_first_opened`, `desktop_account_connected`,
  `desktop_autorecord_enabled`, `first_recording_completed`,
  `first_result_viewed`, `first_value_session_completed`.
- `surface`: enum: `public_web`, `desktop_native`, `auth_web`,
  `cabinet_web`, `embedded_desktop_webview`, `server`.
- `owner`: role: `growth`, `desktop`, `auth_server`, `calendar_policy`,
  `capture_server`, `cabinet`, `product_analytics`, `ops`.
- `occurred_at`: event timestamp, provider-safe.
- `received_at`: server/provider receipt timestamp, if available.
- `identity_rule`: reference to `AnalyticsIdentity`.
- `allowed_fields`: explicit allowlist.
- `forbidden_fields`: explicit denylist.
- `posthog_destination`: `none`, `anonymous`, `identified`.
- `yandex_destination`: `none`, `page_view`, `goal`, `event_parameter`,
  `session_parameter`, `offline_conversion`.
- `retention_category`: reference to `AnalyticsRetentionPolicy`.
- `delivery_mode`: `server_mediated`, `desktop_direct_approved`,
  `web_provider_tag`, `offline_conversion_upload`.
- `measurement_caveats`: list of safe labels.

**Validation rules**:

- Event names are lowercase snake_case and stable.
- Event payload must include no raw email, name, workspace/account name, raw
  user/account/workspace/meeting ID, meeting title, participant, transcript,
  audio, calendar text, local path, object key, token, signed URL, password,
  passcode, device name, or private free text.
- `first_value_session_completed` requires a ready useful result view and must
  not be emitted for recording completion, processing, failure, empty result, or
  auto-record enablement.
- Primary first milestones are counted once per stable pseudonymous user.

## AnalyticsIdentity

Safe identity used for activation analysis.

**Fields**:

- `stable_pseudonymous_user_id`: server-issued opaque string.
- `posthog_distinct_id`: provider-safe value derived from or mapped to the
  stable pseudonymous user ID.
- `workspace_pseudonym`: optional safe metadata dimension.
- `account_pseudonym`: optional safe metadata dimension.
- `device_class`: optional enum, not a raw device name.
- `identity_created_at`, `identity_rotated_at`, `identity_deleted_at`.
- `deletion_state`: `active`, `blocked`, `deletion_requested`,
  `deleted_in_graf_control`, `provider_delete_requested`,
  `provider_delete_unavailable`.

**Validation rules**:

- Raw user/account/workspace IDs are forbidden.
- Email, names, company names, workspace names, device names, meeting IDs, and
  local paths are forbidden.
- If identity rotates, the attribution contract must state whether historical
  analytics remain linked or become measurement gaps.

## AttributionBridge

GRAF-owned bridge between public acquisition and product activation.

**Fields**:

- `graf_attribution_id`: opaque server-issued ID.
- `bridge_token_hash`: optional expiring token hash.
- `created_at`, `expires_at`.
- `source_context`: allowlisted UTM/openstat/referrer category values.
- `yandex_client_id_present`: boolean; actual value must be separately gated.
- `yclid_present`: boolean; actual value must be separately gated.
- `posthog_anonymous_id_present`: boolean.
- `download_intent_event_id`: safe event reference.
- `linked_pseudonymous_user_id`: optional, after authenticated handoff.
- `link_state`: `unlinked`, `download_intent`, `auth_handoff`,
  `account_connected`, `expired`, `withdrawn`, `deleted`.
- `reliability_level`: `counted_unlinked`, `campaign_linked_weak`,
  `campaign_linked_reliable`, `not_linkable`.

**Validation rules**:

- Bridge records must not store raw personal or content-bearing values.
- `desktop_first_opened` is counted even when not campaign-linked.
- `desktop_account_connected` is the first reliable campaign-linked milestone
  unless a later implementation proves a safer earlier handoff.

## ProductTelemetryGate

One required personal acceptance package for normal product use.

**Fields**:

- `gate_version`.
- `copy_version`.
- `required_terms_version`.
- `privacy_policy_version`.
- `personal_data_processing_version`.
- `accepted_at`.
- `accepted_by_pseudonymous_user_id`.
- `accepted_surface`: `desktop_onboarding`, `cabinet`, `auth_web`.
- `providers_disclosed`: PostHog/Yandex flags.
- `direct_desktop_egress_disclosed`: boolean.
- `replay_boundaries_disclosed`: boolean.
- `retention_deletion_disclosed`: boolean.
- `state`: `not_seen`, `accepted`, `withdrawn`, `terms_update_required`,
  `refused_updated_terms`, `limited_to_account_legal_export_deletion`.

**State transitions**:

```text
not_seen -> accepted
accepted -> terms_update_required
accepted -> withdrawn
terms_update_required -> accepted
terms_update_required -> refused_updated_terms
withdrawn -> limited_to_account_legal_export_deletion
refused_updated_terms -> limited_to_account_legal_export_deletion
```

**Validation rules**:

- Normal desktop/cabinet/authenticated product use is blocked unless state is
  `accepted`.
- The gate must be one clear step unless terms or telemetry scope changes.
- Acceptance cannot authorize future broader collection outside the approved
  event/field contract.

## PageClassAnalyticsPolicy

Per-page-class Yandex/PostHog browser collection decision.

**Fields**:

- `page_class`: enum covering public landing, download, legal, login/signup,
  auth callback, cabinet home, onboarding, settings, recording list,
  meeting/result detail, upload, playback, deletion, admin, embedded desktop
  webview, and error pages.
- `url_title_referrer_status`: `safe`, `needs_sanitization`, `blocked`.
- `page_view_allowed`: boolean.
- `safe_event_allowed`: boolean.
- `posthog_replay_allowed`: boolean.
- `yandex_webvisor_allowed`: boolean.
- `click_map_allowed`: boolean.
- `scroll_map_allowed`: boolean.
- `form_analytics_allowed`: boolean.
- `offline_conversion_allowed`: boolean.
- `masking_contract_status`: `not_reviewed`, `passed`, `replay_unavailable`,
  `blocked`.
- `dashboard_caveat`.
- `qa_evidence`.
- `legal_status`: `not_started`, `in_review`, `approved`, `blocked`.

**Validation rules**:

- If URL/title/referrer/events/provider parameters are unsafe, all provider
  collection for the page class is blocked.
- If page views/events are safe but replay proof is missing, page views/events
  may proceed and replay/maps/forms must be disabled.
- Real-user best-effort replay from unapproved page classes is prohibited.

## ReplayMaskingContract

Shared replay policy for PostHog Session Replay and Yandex Webvisor.

**Fields**:

- `page_class`.
- `default_masking`: must be `mask_by_default` for authenticated/product pages.
- `input_suppression`: required.
- `private_dom_hidden`: required.
- `safe_ui_allowlist`: list of neutral selectors/regions.
- `forbidden_replay_payloads`: denylist.
- `posthog_rules`: `ph-no-capture`, `ph-mask`, `ph-ignore-input`, or approved
  equivalents.
- `yandex_rules`: `ym-disable-keys`, `ym-hide-content`, disabled record-all
  fields, or approved equivalents.
- `qa_fixture`.
- `evidence_status`.
- `launch_state`: `replay_allowed`, `replay_unavailable`, `blocked`.

**Validation rules**:

- Inputs, textareas, editors, transcript/result content, names, participants,
  meeting titles, workspace/account names, local paths, tokens, signed URLs,
  payment/contact fields, calendar text, and free text must be hidden or
  suppressed.
- Only neutral UI regions may be allowlisted.
- Replay disabled state must be visible in dashboard/evidence.

## ParallelMeasurementRoute

One row in the measurement matrix.

**Fields**:

- `event_or_page`.
- `surface`.
- `posthog_mode`: `none`, `page_view`, `anonymous_event`, `identified_event`,
  `session_replay`.
- `yandex_mode`: `none`, `page_view`, `goal`, `session_parameter`,
  `user_parameter`, `webvisor`, `click_map`, `scroll_map`, `form_analytics`,
  `offline_conversion`, `replay_disabled`.
- `reason`.
- `allowed_fields`.
- `forbidden_fields`.
- `identity_rule`.
- `retention_rule`.
- `dashboard_owner`.
- `qa_evidence`.

**Validation rules**:

- Shared PostHog/Yandex events require a stated advertising or attribution
  reason.
- Product detail does not fan out to Yandex by default.
- Yandex offline conversions default to `desktop_account_connected` and
  `first_value_session_completed`.

## AnalyticsRetentionPolicy

Category-specific retention and deletion truth.

**Fields**:

- `category`: `attribution_bridge`, `posthog_product_events`,
  `posthog_session_replay`, `yandex_page_events`, `yandex_webvisor`,
  `yandex_offline_conversions`, `delivery_gap`, `exported_report`.
- `minimum_retention_days`: baseline `90`, unless shorter.
- `maximum_retention_days`: to be decided per category before implementation.
- `delete_on_user_request`: `graf_controlled`, `provider_supported`,
  `aggregate_only`, `not_available`, `manual_process`.
- `provider_delete_method`.
- `aggregate_report_truth`.
- `exported_report_truth`.

**Validation rules**:

- No category may promise universal erasure outside GRAF control.
- Exported dashboards/screenshots/ad imports must be described separately.

## AnalyticsDeliveryGap

Safe caveat when approved analytics was not delivered.

**Fields**:

- `gap_type`: `provider_blocked`, `script_blocked`, `sdk_error`,
  `network_unavailable`, `retry_exhausted`, `consent_withdrawn`,
  `page_class_blocked`, `replay_unavailable`.
- `surface`.
- `event_or_page_class`.
- `count_bucket`.
- `time_bucket`.
- `safe_reason`.
- `recovery_status`: `none_needed`, `retried`, `recovered`, `unrecovered`.

**Validation rules**:

- No raw identities, meeting content, local paths, secrets, provider payload
  dumps, cookies, or client IDs.
- Delivery gaps are dashboard caveats, not user-facing product errors.

## ActivationDashboard

Report surface for the product/growth owner.

**Fields**:

- `dashboard_name`.
- `owner`.
- `primary_workspace`: `posthog`.
- `secondary_workspace`: optional `yandex`.
- `funnel_steps`.
- `safe_dimensions`.
- `caveats`.
- `internal_activity_disclosure`.
- `replay_drilldown_status`.
- `offline_conversion_status`.

**Validation rules**:

- The main source-to-first-value journey must be in PostHog.
- Yandex dashboards support web/ad/replay/offline conversion interpretation but
  are not the product source of truth.
- Reports disclose that internal/support/smoke/test activity is counted by
  default.
