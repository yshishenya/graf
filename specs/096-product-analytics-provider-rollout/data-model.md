# Data Model: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

This model describes logical rollout records and validation artifacts. It does not mandate a database migration unless later tasks choose to persist some records inside GRAF.

## ProviderRolloutRecord

Represents the overall rollout state for PostHog and Yandex.

**Fields**:

- `feature`: `096-product-analytics-provider-rollout`
- `provider`: `posthog`, `yandex_metrica`
- `surface`: `posthog_primary`, `yandex_all_pages`, `yandex_offline`
- `mode`: `disabled`, `configured`, `smoke_ready`, `live`, `rolled_back`, `blocked`
- `owner_role`: product/operator role, no personal name required in committed evidence
- `runtime_scope`: redacted summary of enabled routes/pages/events
- `blockers`: list of non-secret blocker codes
- `evidence_ref`: path to metadata-only evidence
- `updated_at`: timestamp or date

**Validation rules**:

- `live` requires provider smoke evidence, secret inventory, dashboard readiness, rollback plan, and no-secret scan.
- Yandex `live` does not imply paid campaign readiness.
- PostHog `live` does not imply PostHog session replay is enabled.

## PostHogWorkspace

Represents the self-hosted primary analytics workspace.

**Fields**:

- `domain`: separate analytics domain, `analytics.2brain.pro`
- `placement`: `same_production_server`
- `portable`: true
- `retention_days_min`: integer, at least `90`
- `autocapture_scope`: `all_browser_rendered_pages`
- `session_replay_state`: `disabled`, `approved_page_classes`, `blocked`
- `credential_suppression_state`: `missing`, `configured`, `verified`
- `rbac_state`: `not_configured`, `configured`, `verified`
- `audit_evidence_state`: `missing`, `configured`, `verified`
- `provider_lifecycle_truth_state`: `missing`, `documented`, `verified`
- `backup_state`: `not_configured`, `configured`, `restore_rehearsed`
- `resource_limit_state`: `not_configured`, `configured`, `smoke_verified`
- `resource_thresholds`: metadata-only summary of CPU, memory, disk, network, log, backup, disk-full, and alert thresholds
- `deploy_handoff_state`: `not_configured`, `dry_run_documented`, `dry_run_verified`
- `move_out_state`: `not_documented`, `documented`, `rehearsed`

**Validation rules**:

- `autocapture_scope=all_browser_rendered_pages` requires `credential_suppression_state=verified`.
- Live provider mode requires `rbac_state=verified`, `audit_evidence_state=verified`, and `provider_lifecycle_truth_state=verified`.
- `live` provider mode requires backup and rollback documentation.
- Same-server live mode requires concrete resource thresholds and evidence that analytics load rolls back or degrades measurement before starving normal GRAF workflows.
- Same-server live mode requires `deploy_handoff_state=dry_run_verified` before future production `--execute` or runtime-update approval.
- Move-out documentation must preserve event names, identity rules, dashboard definitions, and consent/disclosure copy.

## PostHogDeliveryRoute

Represents a route that delivers product analytics into PostHog.

**Fields**:

- `route`: `server_mediated`, `web_direct`, `desktop_direct`
- `surfaces`: page classes, server events, or desktop event subset
- `events`: explicit event names or `autocapture`
- `identity_rule`: pseudonymous user, anonymous public, bridge token, or desktop-safe identity
- `credential_exclusions`: required suppressed values
- `disclosure_state`: `missing`, `drafted`, `approved`
- `rbac_audit_rule`: role boundary and audit expectation for route visibility, dashboard access, exports, and operator changes
- `retention_deletion_truth`: truthful statement for provider-held data, aggregates, backups, dashboard exports, and deletion limitations
- `smoke_state`: `not_run`, `dry_run_pass`, `live_safe_pass`, `failed`
- `retry_loss_rule`: bounded retry, no retry, or measurement gap
- `rollback_switch`: runtime flag or operator action
- `dashboard_caveat`: required caveat when this route feeds dashboards

**Validation rules**:

- PostHog delivery may be direct because PostHog is first-party.
- Every route must declare RBAC/audit expectations, retention/deletion truth, and dashboard caveats before readiness can pass.
- Desktop direct route must not send data to Yandex.
- Raw credential material is invalid for every route.

## YandexMeasurementSurface

Represents the reused 093 production counter as the expandable Yandex surface.

**Fields**:

- `counter_strategy`: `reuse_093_production_counter`
- `public_baseline`: `/`, `/download`
- `all_pages_state`: `blocked`, `inventory_ready`, `partially_live`, `live`
- `offline_state`: `disabled`, `configured`, `live`
- `webvisor_state`: `disabled`, `approved_public_only`, `approved_page_classes`
- `direct_linkage_state`: `not_linked`, `linked`, `blocked`
- `counter_id_source`: runtime-only, never committed
- `retention_deletion_caveat`: truthful statement for Yandex-held page/ad/offline data and GRAF deletion limitations
- `offline_conversion_lifecycle_state`: `not_documented`, `documented`, `verified`

**Validation rules**:

- Future pages are blocked for Yandex until inventory approval.
- Yandex offline live upload is limited to two product milestones.
- Yandex does not receive content-bearing PostHog autocapture exports.
- Yandex dashboard readiness requires `offline_conversion_lifecycle_state=verified` for offline conversion reports.

## PageClassInventoryEntry

Represents one current or future browser-rendered page class.

**Fields**:

- `page_class`: stable identifier
- `examples`: route examples with no live IDs
- `posthog_autocapture_state`: `enabled`, `non_browser`, `temporarily_disabled_by_rollback`
- `posthog_replay_state`: `disabled`, `approved`, `unavailable`
- `yandex_state`: `approved_page_view_event`, `blocked`, `replay_unavailable`
- `credential_suppression`: required suppressed credential/material classes
- `sensitivity`: `public`, `auth`, `product`, `meeting`, `admin`, `error`, `embedded`
- `expected_product_visible_data`: safe description, not raw data
- `legal_basis_status`: `pending`, `approved`, `blocked`
- `qa_status`: `pending`, `passed`, `blocked`
- `dashboard_purpose`: product, acquisition, diagnostic, blocked
- `rollback_behavior`: disable flag or remove snippet

**Validation rules**:

- Every current browser-rendered page class must have PostHog autocapture enabled or be explicitly non-browser/not-rendered.
- Every future page inherits PostHog autocapture after global credential suppression exists.
- Every future page is blocked for Yandex until added to inventory.

## OfflineConversionRecord

Represents one Yandex offline conversion row before upload.

**Fields**:

- `event_name`: `desktop_account_connected` or `first_value_session_completed`
- `datetime`: past timestamp accepted by Yandex
- `identity_kind`: `UserId`, `ClientId`, or `Yclid`
- `identity_value_source`: pseudonymous/attribution bridge reference, never raw committed value
- `purchase_id_or_dedupe_key`: stable synthetic/hashed dedupe value
- `upload_batch_id`: metadata-only batch reference
- `upload_state`: `queued`, `uploaded`, `confirmed`, `failed`, `duplicate_suppressed`
- `provider_response_ref`: metadata-only reference

**Validation rules**:

- No product event outside the two approved names is valid.
- At least one Yandex-supported identity key must exist before live upload.
- `UserId` requires prior rendered-page binding through Yandex `setUserID` and
  `userParams` for the same GRAF pseudonymous user ID.
- `ClientId` and `Yclid` require real runtime resolver values and cannot be
  replaced by the GRAF pseudonymous user ID.
- Duplicate upload must be suppressed or marked before retry.
- Upload evidence must not include raw identity values, Yandex client IDs, cookies, or OAuth tokens.

## ProviderSecretInventoryEntry

Represents one runtime secret or provider ID reference.

**Fields**:

- `name`: logical secret or runtime ID name
- `owner_role`: operator role
- `storage_source`: secret file, runtime environment, provider dashboard
- `target_service`: `posthog_stack`, `rec-api`, smoke runner, or operator-only
- `committed_default`: placeholder/empty only
- `rotation_note`: how rotation is handled
- `propagation_test`: focused test or smoke scenario
- `evidence_state`: `missing`, `redacted_recorded`, `verified`

**Validation rules**:

- Secret values are never committed.
- Live counter IDs and client IDs are not committed in evidence.
- `rec-processing-worker` must not receive product analytics provider secrets unless a later task proves it needs them.

## ProviderLifecycleRecord

Represents the truthful retention/deletion statement for a provider-held data
class. This record prevents provider setup from promising deletion behavior that
GRAF cannot technically guarantee.

**Fields**:

- `provider`: `posthog`, `yandex_metrica`, `graf_metadata`
- `data_class`: activation event, autocapture event, replay recording, offline conversion, provider aggregate, dashboard export, delivery-gap record, backup
- `storage_location`: provider workspace, provider backup, GRAF metadata store, committed evidence, or operator-only export
- `retention_days`: number or provider-configured policy reference
- `deletion_scope`: `deleteable_by_graf`, `provider_operator_action`, `aggregate_only`, `not_collected`, `not_promised`
- `backup_behavior`: retained until backup expiry, immediately removed, or not applicable
- `export_policy`: forbidden, metadata-only, operator-only, or dashboard aggregate
- `dashboard_caveat`: required user/operator-facing caveat
- `evidence_state`: `missing`, `documented`, `verified`

**Validation rules**:

- Committed evidence may never include content-bearing provider exports.
- Provider deletion copy must distinguish GRAF-controlled deletion from provider aggregates, backups, offline conversions, and exported dashboards.
- PostHog content-bearing analytics may remain inside self-hosted PostHog only; Yandex must not receive those exports.
- Dashboard readiness requires lifecycle caveats for every provider dashboard or report.

## ProviderSmokeResult

Represents a dry-run or live-safe smoke result.

**Fields**:

- `smoke_name`
- `provider`
- `mode`: `dry_run`, `live_safe`
- `environment`: local, production dry-run, production execute
- `runtime_config_seen`: boolean
- `delivery_status`: pass/fail/blocked
- `dashboard_status`: visible/not_visible/not_applicable
- `secret_status`: present/redacted/missing
- `private_payload_status`: none_found/blocked/found
- `access_model_status`: not_checked/pass/fail/blocked
- `lifecycle_status`: not_checked/pass/fail/blocked
- `deploy_dry_run_status`: not_checked/pass/fail/not_applicable
- `rollback_status`: not_checked/pass/fail

**Validation rules**:

- No raw provider payload dumps.
- Live-safe smoke uses synthetic/internal metadata only.
- Failures are measurement/operator blockers, not user-facing product failures.
- PostHog live readiness requires access model, lifecycle, resource threshold, and deploy dry-run statuses to pass or be explicitly blocked with non-secret reasons.

## DashboardReadinessRecord

Represents one dashboard or report surface.

**Fields**:

- `dashboard_name`
- `provider`: PostHog or Yandex
- `owner_role`
- `purpose`
- `events_or_pages`
- `internal_activity_caveat`
- `retention_deletion_caveat`
- `provider_gap_caveat`
- `access_model_caveat`
- `campaign_caveat`
- `status`: `not_started`, `drafted`, `verified`, `blocked`

**Validation rules**:

- Every dashboard must include caveats before launch evidence can pass.
- Yandex campaign dashboard readiness does not approve paid campaign launch.

## RollbackPlan

Represents rollback controls for provider delivery.

**Fields**:

- `target`: PostHog delivery, PostHog autocapture, PostHog replay, Yandex all-pages, Yandex offline upload, provider validation mode
- `disable_method`: runtime flag, secret removal, route removal, provider setting, DNS/service stop
- `expected_product_impact`: should be `measurement_gap_only`
- `verification_command`
- `restoration_command`
- `owner_role`

**Validation rules**:

- Rollback must preserve normal product workflows.
- Rollback must record delivery gaps and dashboard caveats.
- Rollback must not delete evidence needed for audit.
