# Data Model: Complete Recording Workflows

## Design Rules

- Extend current owner/workspace-scoped meeting, outcome, access, egress, and
  deletion entities; do not create a parallel meeting domain.
- Keep raw meeting content out of ordinary audit, analytics, diagnostics,
  invitations, tokens, screenshots, and committed evidence. Langfuse AI
  observations, Temporal History, and the retained Generation Call ledger are
  explicit plaintext observability stores with complete meeting/model content.
- Store hashes of share/invite secrets, never raw secrets.
- Use explicit typed policy fields for authorization decisions; do not hide
  security semantics only in free-form metadata.
- Preserve historical grants and outcome sets during migration.
- Deletion wins new generation, invite, share, export, acceptance, and product
  publication races, but it does not erase retained observability copies.

## Existing Entities Reused Without A New Store

### Recording Session / Local Package

Authority remains the native capture controller, local manifest, v5 writer,
local store, and upload queue. Feature 121 adds presentation and validation but
does not add another persisted capture entity.

Relevant truth:

- local recording ID and meeting correlation;
- source readiness and degraded state;
- active/paused privacy intervals;
- finalization and local custody;
- upload/retry/purge state;
- v5 artifact identity and format.

### Meeting

The existing `meetings` row stays the durable server identity. Add only the
accepted-summary pointer needed to make candidate regeneration safe:

| Field | Type | Rules |
|---|---|---|
| `current_outcome_set_id` | optional UUID | Same workspace/meeting; points only to an accepted active outcome set; cleared/blocked by deletion. |

The pointer changes only in the same transaction that accepts a generated
candidate. A failed or cancelled candidate never changes it.

### Processing Result, Transcript Segments, Speaker Turns, Playback

Reused as source truth. Summary templates and sharing never rewrite provider
rows or playback artifacts. Feature 120 remains responsible for a canonical
export snapshot over the selected result/revision.

## New Entity: Summary Template

Table concept: `summary_templates`.

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable internal identity. |
| `workspace_id` | UUID | Required tenant scope for personal and built-in projections. |
| `owner_user_id` | optional UUID | Required for personal templates; absent for seeded built-ins. |
| `template_key` | string | Stable bounded key, unique within owner/workspace scope. |
| `kind` | enum | `builtin` or `personal`. |
| `name` | string | 1–80 visible characters; original Russian copy. |
| `purpose` | string | 1–240 visible characters; no meeting content. |
| `sections_json` | ordered list | Allowlisted section keys only: summary, key points, decisions, action items, follow-ups, risks, questions, evidence. |
| `output_language` | enum/string | Allowlisted supported output language; independent of UI and transcript language. |
| `detail_level` | enum | `brief`, `standard`, or `detailed`. |
| `version` | positive integer | Increments for every personal edit. |
| `status` | enum | `active`, `archived`, or `deleted`. |
| `created_at`, `updated_at` | timestamp | Server-owned timestamps. |

### Constraints

- Built-ins are immutable in product flows; customization duplicates to a new
  personal template.
- A personal template belongs to one user in one workspace in v1.
- Archiving prevents new selection but preserves historical provenance.
- Deleting a personal template is soft lifecycle deletion while referenced by
  an outcome set; historical meetings retain safe name/key/version projection.
- `sections_json` is schema-validated and cannot contain free-form model/system
  instructions or markup.

## Existing Entity Extended: Meeting Outcome Set

Extend `meeting_outcome_sets` and generation attempts rather than creating a
second summary store.

| Field | Type | Rules |
|---|---|---|
| `template_id` | optional UUID | Required for new template-backed generations; same workspace. |
| `template_key` | string | Immutable safe provenance projection. |
| `template_version` | positive integer | Version used for this generation. |
| `output_language` | string | Selected summary language. |
| `detail_level` | enum | Selected bounded detail. |
| `revision_state` | enum | `candidate`, `accepted`, `superseded`, or `rejected`; generation failure belongs to the attempt, not the outcome set. |
| `requested_by_user_id` | optional UUID | Actor for manual regeneration; null only for policy-owned first generation. |
| `accepted_by_user_id` | optional UUID | Required when a candidate becomes accepted manually. |
| `accepted_at` | optional timestamp | Set atomically with meeting pointer. |
| `supersedes_outcome_set_id` | optional UUID | Same meeting/workspace only. |

Generation attempts receive the same template key/version/language/detail
inputs plus durable orchestration and AI provenance:

| Field | Type | Rules |
|---|---|---|
| `candidate_id` | UUID | Stable idempotency key and workflow correlation. |
| `source_result_id` | UUID | Pinned selected transcript/result revision. |
| `requested_by_user_id` | optional UUID | Actor who requested this candidate; null only for policy-owned generation and legacy rows. |
| `prompt_name` | bounded string | Exact allowlisted format-specific Langfuse prompt key; no prompt content. |
| `prompt_version` | positive integer | Exact promoted Langfuse version used. |
| `prompt_source` | enum | `langfuse_production` or `verified_promoted_snapshot`. |
| `prompt_definition` | bounded text/JSON | Exact uncompiled prompt snapshot resolved in the first Temporal activity; never exported as a standalone trace field, while its compiled instructions are part of the exact logical model request generation input. |
| `prompt_config` | bounded JSON | Strictly validated exact Langfuse config containing selected model route, allowlisted generation settings, strict response schema, and bounded version identifiers; no endpoint, key, header, tool, or secret. |
| `prompt_hash` | fixed hash | Digest of the canonical self-contained prompt plus config persisted atomically. |
| `output_schema_version` | bounded string | Exact schema identifier from the pinned config. |
| `model_route` | bounded string | Selected LiteLLM route from the pinned config, initially `gpt-5.6-luna`. |
| `model_parameters` | bounded JSON | Sanitized allowlisted request parameters used for the actual call. |
| `workflow_id` | bounded string | Deterministic `outcome-generation/<candidate_id>`. |
| `workflow_run_id` | optional bounded string | Latest operational correlation for retained Temporal History. |
| `langfuse_trace_id` | bounded string | Deterministic trace correlation derived from candidate ID; does not gate candidate readiness. |
| `temporal_transcript_hash` | fixed hash | Canonical pinned transcript digest reconstructed from plaintext chunks. |
| `temporal_transcript_chunk_count` | positive integer | Deterministic bounded plaintext chunk count. |
| `status` | enum | `queued`, `generating`, `blocked_dependency`, `candidate`, `failed`, or `cancelled`. |
| `attempt_count` | positive integer | Durable business attempt count, not nested SDK retry count. |
| `failure_code` | optional enum/string | Bounded retryable/terminal reason; no provider body. |

The uncompiled prompt/config snapshot is a cached copy of one promoted Langfuse
version, not an independently editable server prompt. The complete canonical
transcript is persisted in Temporal History as deterministic plaintext chunks.
The exact compiled request, transcript, raw response, and validated result are
also retained in the Generation Call ledger and Langfuse observation tree.
Generation Call rows are the only authority for Langfuse delivery state; any
candidate/attempt-level delivery badge or metric is a read-time aggregate that
is `confirmed` only when every completed call row is confirmed and otherwise
`pending`.

### Generation Call Delivery Ledger

`generation_calls` is an additive retained observability table, deliberately
outside the meeting/candidate deletion cascade. It records each provider egress
and the complete plaintext content needed to deliver one deterministic Langfuse
generation without replaying inference:

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable retained row identity. |
| `workspace_id` | UUID | Required retained tenant/operations scope; ordinary cabinet meeting access does not expose this table. |
| `meeting_id` | UUID | Stable opaque correlation copied from the meeting; no cascading foreign key. |
| `candidate_id` | UUID | Stable opaque generation-attempt correlation; no cascading foreign key. |
| `provider_attempt`, `call_sequence` | positive integer | Distinguishes genuinely repeated provider calls from export retry. |
| `trace_id`, `observation_id` | bounded strings | Deterministic from candidate plus provider attempt/call sequence. |
| `call_state` | enum | `reserved`, `completed`, `failed`, or `ambiguous`; ambiguous means egress may have occurred but no response reached durable storage. |
| `started_at`, `completed_at` | timestamps | Original call timing used when publishing later. |
| `actual_provider`, `actual_model` | optional bounded string | Exact per-call response provenance from LiteLLM when available; never a credential or endpoint. |
| `provider_request_id` | optional bounded string | Safe per-call gateway correlation only. |
| `token_usage` | optional bounded JSON | Exact normalized per-call usage returned by LiteLLM/provider; absent means `unknown`, never an estimate presented as fact. |
| `cost_details` | optional bounded JSON | Exact per-call returned cost when available; otherwise omitted so Langfuse may calculate from its model-price catalog or display unknown. |
| `request_json` | bounded JSON | Exact compiled logical request with the complete canonical transcript. |
| `transcript_text` | bounded text | Complete canonical transcript retained verbatim. |
| `raw_response_json` | bounded JSON/text | Exact provider response available to GRAF. |
| `validated_result_json` | bounded JSON | Exact locally validated structured result. |
| `request_hash`, `transcript_hash`, `raw_response_hash`, `validated_result_hash` | fixed hashes | Equality and tamper evidence across GRAF, Temporal, and Langfuse. |
| `export_status` | enum | `pending` or `confirmed`; a delivery failure stays pending and does not gate candidate readiness. |
| `export_attempt_count` | non-negative integer | Delivery attempts only; never provider/model attempts. |
| `last_export_attempt_at`, `next_export_attempt_at`, `export_confirmed_at` | optional timestamp | Durable background-delivery scheduling and evidence. |
| `last_export_error_code` | optional bounded enum/string | Content-free operational reason; never clears retained content. |

The sole publisher reads this retained row, verifies hashes, and reuses the same
observation ID. Confirmation updates delivery status but does not clear content;
every delivery error leaves the row pending for durable retry. Meeting deletion
does not cascade to this table and cannot cancel its delivery. RLS/policy allows
only the outcome worker and least-privilege deployment operator to query retained
rows by `workspace_id` or stable opaque IDs; normal cabinet meeting routes never
read them. An `ambiguous` call never fabricates missing raw output or claims
complete content observability.

### Generation Attempt State Transitions

```text
queued → generating → candidate
queued → blocked_dependency → queued
queued/generating → failed
queued/generating/blocked_dependency → cancelled
```

Outcome sets separately use:

```text
candidate → accepted
candidate → rejected
accepted → superseded (only when a newer candidate is accepted)
```

Rules:

- The last accepted set remains current during generation and after failure.
- Accepting a candidate and superseding the prior set are one transaction.
- Sharing/export reads the meeting's accepted pointer, never “latest by time.”
- Deletion blocks new generation and prevents candidate acceptance.
- Duplicate dispatch reuses `workflow_id`; duplicate activity delivery reuses
  `candidate_id` and cannot create a second publishable candidate.
- Langfuse export outage leaves the candidate ready and changes only the
  background export status; retry cannot repeat the model call. If no promoted
  version or verified snapshot can be resolved, the attempt enters
  `blocked_dependency` before model egress.

## New Entity: Prompt Optimization Run

`prompt_optimization_runs` stores durable control/provenance for one
deployment-operator-triggered GEPA run. It is global to the one Langfuse
project, has no cabinet/workspace authorization path, and is accessible only to
the privileged operator service/database role. Feature 121 uses synthetic
datasets only; owner-controlled checkpoints remain the resume authority while
Langfuse observations and Temporal History may retain the full plaintext
synthetic examples, outputs, feedback, and optimizer state.

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable workflow/idempotency key. |
| `deployment_scope` | bounded literal | Required literal `global`; matches project-global prompt labels. |
| `initiated_by_actor_id` | bounded opaque string | Deployment-operator audit identity; never user-facing. |
| `prompt_name` | bounded string | One allowlisted outcome-format prompt. |
| `source_prompt_version` | positive integer | Exact production version pinned at start. |
| `source_config_hash` | fixed hash | Canonical prompt/config hash. |
| `train_dataset_ref`, `development_dataset_ref`, `heldout_dataset_ref` | opaque bounded strings | Immutable owner-controlled synthetic dataset version references; no content. |
| `dataset_manifest_hashes` | bounded JSON | Hashes and counts only. |
| `optimizer_version` | bounded string | Exact `gepa==0.1.4` baseline. |
| `adapter_version`, `metric_versions` | bounded JSON | Exact reproducibility identifiers. |
| `reflection_prompt_name`, `reflection_prompt_version`, `reflection_config_hash` | bounded strings/integer | Exact promoted `graf/prompt-optimization/reflection` contract. |
| `judge_prompt_refs` | bounded JSON | Exactly three `{prompt_name, prompt_version, config_hash}` records for faithfulness, action-items, and completeness. |
| `budget` | bounded JSON | Maximum calls, tokens/cost, wall time, and concurrency. |
| `deadline_at` | timestamp | Immutable absolute run deadline checked before every egress and after retry. |
| `workflow_id`, `workflow_run_id` | bounded strings | Deterministic `prompt-optimization/<id>` and operational run correlation. |
| `run_artifact_ref` | opaque bounded string | Shared owner-controlled object/persistent-volume reference; never a worker-local path or telemetry value. |
| `checkpoint_revision`, `checkpoint_hash`, `checkpoint_schema_version` | integer/hash/string | Latest complete immutable server-generated checkpoint; DB pointer advances atomically after upload and restore verifies prefix/hash/schema/optimizer version. |
| `candidate_prompt_version` | optional positive integer | Langfuse candidate version created after validation. |
| `candidate_prompt_hash`, `candidate_config_hash` | optional fixed hashes | Exact published text/config; GEPA candidate config must equal source config. |
| `aggregate_scores` | bounded JSON | Content-free train/development/held-out aggregates and hard-gate outcomes. |
| `rollback_prompt_version` | positive integer | Prior protected production version. |
| `approval_state` | enum | `not_requested`, `awaiting_human`, `approved`, `rejected`, `expired`. |
| `approval_expires_at` | timestamp | Immutable deterministic deadline, at most seven days after candidate readiness. |
| `approval_action_id`, `approved_by_actor_id`, `approved_at` | optional UUID/bounded string/timestamp | Single-use audit action plus deployment-operator identity stored in DB, not Temporal history. |
| `status` | enum | `queued`, `running`, `paused`, `candidate`, `rejected`, `expired`, `failed`, `cancelled`, `promoted`, `rolled_back`. |
| `failure_code` | optional bounded enum | No raw optimizer/provider output. |

State transitions:

```text
queued → running → candidate → promoted
queued/running → paused → running
queued/running/paused → failed | cancelled
candidate → rejected | expired
promoted → rolled_back
```

Rules:

- `prompt_optimization_runs` database rows contain only run ID, immutable
  references/hashes, budgets, version IDs, aggregate status, and bounded errors;
  Temporal History may retain the complete plaintext synthetic inputs, outputs,
  reflection, judge feedback, and optimizer state required for debugging.
- Source, reflection, and all three judge prompt/config versions are independently pinned
  before the first optimization model call; no optimizer model setting comes
  from code.
- Only a held-out-passing finalist creates a candidate. It receives no manually
  assigned label, Langfuse-managed `latest` is ignored, and candidate/source
  canonical config hashes must match after re-reading the exact version.
- `production` promotion requires hard gates, held-out comparison, explicit
  deployment-operator approval, a per-prompt lock, expected-source recheck and
  post-verification, plus an existing rollback version.
- A stale run whose source production version changed cannot promote without a
  new comparison and approval.

## New Entity: Prompt Optimization Call Ledger

`prompt_optimization_call_ledger` is the metadata-only authority for GEPA
budget reservation and resume deduplication. It is deployment-scoped and uses
the same privileged access boundary as the run.

| Field | Type | Rules |
|---|---|---|
| `run_id`, `call_key` | UUID/bounded string | Composite unique key; call key hashes phase, candidate, dataset item and exact prompt/config versions without content. |
| `phase` | enum | `task`, `reflection`, `judge_faithfulness`, `judge_action_items`, `judge_completeness`. |
| `prompt_version`, `config_hash`, `model_route` | bounded values | Exact invocation provenance. |
| `reserved_token_ceiling`, `reserved_cost_ceiling` | integer/decimal | Durable reservation charged before egress. |
| `status` | enum | `reserved`, `succeeded`, `ambiguous`, `failed`. |
| `result_artifact_ref` | optional opaque string | Owner-controlled result reference; no content in PostgreSQL/telemetry. |
| `actual_input_tokens`, `actual_output_tokens`, `actual_cost` | optional bounded numbers | Provider-returned accounting only. |
| `activity_attempt`, `activity_fence`, `lease_expires_at` | integer/UUID/timestamp | New attempts atomically fence old workers; expired reservations become ambiguous. |
| `created_at`, `completed_at` | timestamps | Retry/audit correlation. |

Successful entries are reused after resume. A crash after egress but before
durable success becomes `ambiguous`, consumes its reservation, and follows the
bounded operator policy; the design does not claim impossible exactly-once
provider egress.

## Existing Entity Extended: Meeting Share Grant

Keep `meeting_share_grants` as the shared policy record for internal identity,
workspace/team, and token audiences.

| Field | Type | Rules |
|---|---|---|
| `audience_type` | enum | `user`, `workspace`, `team`, or `link`. Existing recipient grants migrate to `user`. |
| `audience_id` | optional UUID | User/team/workspace identity as applicable; absent for link. |
| `content_scope` | enum | `summary_only` or `full_meeting`. |
| `can_download` | boolean | False by default; never implied by view. |
| `can_export` | boolean | False by default; never implied by view. |
| `share_token_hash` | optional string | Required for recipient/link URL; raw token returned once. |
| `expires_at` | optional timestamp | Required by policy for public link; optional for internal grants. |
| `rotated_at` | optional timestamp | Token rotation evidence. |
| `last_used_at` | optional timestamp | Content-free abuse/operations signal. |
| `status` | enum | `active`, `revoked`, `expired`, `blocked`, or `deleted`. |

### Constraints

- Default creation is user audience + summary-only + no download/export.
- Workspace/team/link grants require an explicit policy check and confirmation.
- Link tokens use high-entropy random values and one-way hashes; lookup is
  bounded and rate-limited.
- Summary-only authorization uses a narrow response projection and cannot call
  playback/transcript/export/private-template routes.
- Deletion changes all active grants to terminal blocked/deleted state before
  content workers can publish new output.
- Existing recipient-specific authenticated links keep their semantics during
  migration.

## New Entity: Meeting Share Invitation

Table concept: `meeting_share_invitations`. This entity exists only because an
email address is not yet an internal user identity and delivery has a separate
lifecycle.

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Stable invitation identity. |
| `workspace_id`, `meeting_id` | UUID | Required tenant/meeting scope. |
| `invited_by_user_id` | UUID | Authorized owner actor. |
| `normalized_address_hash` | string | Lookup/deduplication hash; no raw address in audit. |
| `encrypted_delivery_address` | encrypted value/reference | Accessible only to bounded delivery workflow; removed after terminal expiry/resolution according to policy. |
| `content_scope` | enum | `summary_only` or `full_meeting`. |
| `can_download`, `can_export` | boolean | False by default. |
| `token_hash` | string | One-way invitation token hash. |
| `status` | enum | `pending`, `sent`, `accepted`, `expired`, `revoked`, `failed`, `deleted`. |
| `resolved_user_id` | optional UUID | Set only after authenticated, verified account match. |
| `expires_at`, `sent_at`, `accepted_at`, `revoked_at` | timestamps | Lifecycle evidence. |
| `failure_code` | optional bounded string | Content-free delivery failure reason. |

### Invitation State Transitions

```text
pending → sent → accepted
pending/sent → failed
pending/sent → expired
pending/sent → revoked
any non-deleted → deleted (meeting deletion)
```

Accepting creates or activates a normal user share grant in the same workspace
and terminates the pending invitation. An error never confirms whether an
unrelated private account exists.

## Existing Entities Reused For Audit And Deletion

### Meeting Egress Audit Event

Add bounded event types and metadata keys only:

- template created/updated/archived;
- summary generation requested/failed/accepted/rejected;
- summary generation queued/started/retried/cancelled with prompt/config/schema
  versions and hashes, workflow ID, optional Langfuse trace ID, selected/actual
  provider-model provenance, and bounded failure class;
- deployment audit records prompt optimization queued/resumed/candidate/
  rejected/promoted/rolled back with opaque synthetic manifest hashes, version
  IDs, aggregate gates, operator actor ID, and bounded status only;
- grant created/updated/rotated/revoked/expired;
- invitation requested/sent/accepted/failed/revoked;
- protected share access allowed/denied;
- export entry selected and deletion blocked.

No template body, email address, transcript/summary text, token, URL, or private
meeting title is stored.

### Deletion Accounting

Register:

- personal template rows only when the meeting owns no reusable definition;
- outcome candidates/accepted revisions and attempts;
- retained plaintext Generation Call rows, Temporal outcome History, and
  Langfuse trace/observation IDs as explicit observability copies outside the
  meeting-deletion cascade;
- synthetic prompt-optimization rows, call-ledger entries, and shared
  checkpoints under a separate deployment retention/purge command that removes
  only GRAF-owned rows/checkpoints; they have no meeting linkage in feature 121,
  and their Langfuse observations and Temporal History remain retained rather
  than being represented as purge targets;
- share grants, token hashes, invitations, and delivery workflow state;
- any temporary export or delivery object created by existing services.

Deletion reports distinguish active server purge, cancellation of pending
workflow work, invitation delivery limits, backup/replica expiry, previously
exported copies, and external processing limits. They explicitly state that
the plaintext Generation Call ledger, Langfuse observations, and Temporal
History are retained under operator-managed observability retention and are not
failed purge artifacts.

## Authorization Matrix

| Actor | Review full meeting | Review summary-only | Manage templates | Manage shares | Download/export | Delete |
|---|---:|---:|---:|---:|---:|---:|
| Meeting owner | Policy | Yes | Own templates | Yes | Policy | Yes |
| Internal full-meeting grantee | Yes | Yes | No | No | Explicit grant/policy | No |
| Internal summary-only grantee | No | Yes | No | No | Explicit summary export only | No |
| Workspace/team grantee | By grant | By grant | No | No | Explicit grant/policy | No |
| External invitee after verified acceptance | By grant | By grant | No | No | Explicit grant/policy | No |
| Anonymous link viewer | Narrow projection only | By grant | No | No | Disabled by default | No |
| Workspace administrator | Existing policy only; no implicit meeting access | Existing policy only | Built-in/default policy only | Policy administration only | Existing policy | Existing deletion role only |

Prompt optimization is intentionally outside this meeting/workspace matrix.
Only a deployment operator using the privileged command/service role may start,
approve, promote, roll back, or purge it; a workspace administrator receives no
such authority.

## Migration And Compatibility

- Additive migration only; no destructive rewrite of historical recordings,
  results, grants, export packages, or deletion reports.
- Existing `MeetingShareGrant.grantee_user_id` maps to `audience_type=user` and
  keeps existing token behavior.
- Historical outcome sets without template provenance remain readable as
  `legacy_default`; new regeneration requires an explicit template/version.
- Seeded built-ins use stable keys and version 1; copy/name/sections remain
  original GRAF product content.
- Tenant RLS policies cover every tenant-owned table; disposable PostgreSQL
  tests also prove ordinary application/workspace roles cannot read or mutate
  deployment-global optimizer tables before migration is eligible.
