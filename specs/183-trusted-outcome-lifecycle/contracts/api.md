# Contract: cabinet/API changes

Exact URL naming may follow repository conventions; request/response semantics below are normative.

## List available type states

`GET /cabinet/meetings/{meeting_id}/summary-types`

The response is one immutable presentation snapshot with top-level
`catalog_version`, `resolved_locale` and `entries`. Every entry is an exact
`SummaryTypeCatalogEntryV1`; the client does not invent names, grouping or
ordering.

### `SummaryTypeCatalogEntryV1`

| Field | Contract |
|---|---|
| `catalog_version` | Exact 1..64-byte catalog/policy version; equals the top-level value |
| `template_key` / `template_version` | Stable type key and exact current generation-template snapshot |
| `resolved_locale` | Supported BCP-47 locale used for both visible strings |
| `localized_name` / `localized_description` | Non-empty localized strings from the same catalog version; no client-authored fallback |
| `catalog_group` / `group_rank` | `personal | built_in | additional`, with the server-materialized stable group order |
| `category` | `personal | general | team_project | people_learning | customer_revenue | high_stakes` |
| `quick_rank` | Nullable unique `uint16`; non-null means the row appears in the compact selector |
| `full_rank` | Unique `uint16` inside `catalog_group`; controls the complete catalog |
| `availability_state` | `available | unavailable | retired` |
| `provenance` | Exact object `{source, evidence_id, rights_state}` where source is `observed_reference | graf_extension | user_owned`, `rights_state` is `not_applicable | cleared | replacement_required | blocked`, evidence ID is opaque/nullable and no local path or private title is exposed |
| `deviation_codes` | Stable sorted subset of `accessibility | localization | privacy | security | deletion_truth | reference_defect | rights | graf_extension`; empty means no documented deviation |

The compact selector sorts all non-null rows by
`(quick_rank, template_key UTF-8 bytes)`. The complete catalog sorts by
`(group_rank, full_rank, template_key UTF-8 bytes)`. Result/generation/source
state changes never reorder either list. `All templates` and `New template` are
fixed navigation/action rows after the compact entries, not fake summary types.
Any visible-string, membership, group, rank, provenance or deviation change
requires a new `catalog_version`; mixed-version entries fail response validation.
Feature 198 owns the built-in snapshot, Feature 199 owns personal-row ranks and
Feature 196 renders the supplied snapshot identically in browser and embedded
macOS.

The compact selector contains exactly the entries with non-null `quick_rank`,
in that rank order. A row with `quick_rank=null` is never silently promoted into
the compact selector; it is reachable only through the `Все форматы` full-catalog
route, which uses the same snapshot and `full_rank` ordering. The full catalog
also contains the fixed `Новый формат` action where the capability permits it.
Opening the full catalog is navigation only and never selects a type or starts
inference. Selecting any row follows the same saved-switch/one-click-ensure
contract as the compact selector.

`rights_state=not_applicable` is legal only for independently designed GRAF
material with no third-party asset/content dependency; `cleared` requires the
owner-controlled evidence record; `replacement_required` allows internal review
but blocks release of the affected visible material; `blocked` removes the
capability from a release snapshot. UI similarity alone does not convert one
state into another, and the client cannot downgrade it.

Each item then exposes lifecycle metadata only:

- `result_state`: `ready | absent`;
- `generation_state`: `idle | preparing | updating | blocked | deferred | error | ambiguous | no_supported_content`;
- `source_state`: `not_ready | transcript_failed | empty | current | stale`;
- a retired custom type may still have `result_state=ready`, but cannot be ensured, refreshed, selected as a new default or used to create new egress;
- `current_outcome_set_id` whenever a current result exists, including while a replacement is `updating`, after an update `error`, or when source freshness is `stale`;
- bounded `attempt_id`, `reason_code`, `retryable`, `next_action` where applicable. `next_action` is one of `wait | retry_safe | switch_type | open_transcript | correct_transcript_language`; `retryable` is derived from `next_action=retry_safe`, and an ambiguous provider outcome never exposes it.

These dimensions are normative and must not be collapsed into a single `unsupported` or generic `error` value. For example, a saved result from a retired type is `ready + retired`; a current result while refresh fails is `ready + error + current`; a result from an older source is `ready + idle|updating + stale`; transcript failure is source-scoped and cannot be reported as summary generation failure.

Feature 196 adds the requesting user's `selected` presentation state; Feature 183 does not persist or mutate a meeting-global selection.

### Public recovery contract

`next_action` is one primary recommendation, not a list of every still-available
control. Its only legal values are:

```text
wait | retry_safe | switch_type | open_transcript |
correct_transcript_language
```

`retryable` is true iff `next_action=retry_safe`. `retry`, `change_focus`,
`wait_for_source_change` and provider-specific actions are never serialized.
The server derives the pair from the locked attempt/source/catalog state and a
versioned capability snapshot; the client never invents or upgrades it.

The mapping order is deterministic:

1. Active work, dependency recovery already scheduled, source processing and an
   ambiguous provider outcome map to `wait`, `retryable=false`.
2. A terminal failure maps to `retry_safe`, `retryable=true` only with an exact
   safe-retry proof: no provider egress occurred, or authoritative reconciliation
   proved no publishable result/side effect, and current source/template/access/
   deletion preconditions permit a new identity. Timeout/connection loss alone
   is never that proof. For a model call the only V1 no-egress authority is the
   exact `failed_pre_egress` state plus authenticated
   `ProviderNoEgressProofV1`; `prepared` work may resume because its mandatory
   pre-egress CAS has not committed. `sending`/`ambiguous` are always wait-only.
3. `transcript_generation_failed` maps to
   `correct_transcript_language` only when that capability is authorized and a
   language correction can invoke Feature 197's exact authenticated/idempotent
   expected-source-revision command; otherwise it maps to
   `wait` while automatic recovery is active, then `open_transcript`.
4. `no_eligible_items` and `no_selected_items` map to `switch_type` only when
   another available type exists in the frozen capability snapshot; otherwise
   they map to `open_transcript`.
5. `focus_no_supported_topic`, `focus_ambiguous` and
   `focus_topic_catalog_capacity_exceeded` map to `open_transcript`. The normal
   focus control remains editable when authorized; changing it creates a new
   request identity, but `change_focus` is not a public recovery enum.
6. A remaining terminal type-scoped state maps to `switch_type` only when the
   current reason explicitly permits another type and one is available;
   otherwise `open_transcript`. Access loss/deletion exposes no private recovery
   detail or action.

The response binds `reason_code`, `next_action`, `retryable` and the capability/
safe-retry proof hash used by this mapping. A contradictory pair fails response
validation rather than becoming a clickable button.

## Read one type

`GET /cabinet/meetings/{meeting_id}/summaries/{template_key}`

- Returns exact current revision and items, or honest state.
- Returns the full `source_state` enum. With `result_state=ready`, source is `current|stale`; with `result_state=absent`, it is `not_ready|transcript_failed|empty|current` according to the canonical source. `stale` requires an existing older-source result. Transcript failure/empty never masquerades as summary error, and stale content remains readable but cannot create new egress.
- Returns current result and replacement-attempt status as separate objects; an `updating` or failed attempt cannot remove or relabel the current result.
- Returns a saved retired-type result read-only; ensure/refresh/default mutation links are absent and no available type is substituted under the retired name.
- Never triggers inference implicitly unless the endpoint is explicitly documented as `ensure`.
- Never returns internal candidate preview as ready content.

### Active copy capability

The read response includes one discriminated `CopyCapabilityV1` for the active
top-strip tab. It is a capability descriptor, not a second content store:

```text
{ kind: summary,
  authorized: true,
  outcome_set_id,
  outcome_content_hash,
  displayed_revision: outcome_set_id }
{ kind: transcript,
  authorized: true,
  source_revision,
  transcript_content_hash,
  displayed_revision: source_revision }
```

`kind=summary` is legal only when the exact painted result is ready and binds
Copy to that `outcome_set_id`; `kind=transcript` is legal only for the exact
painted authorized transcript revision. A disabled capability is the same
discriminated object with `authorized=false` and one bounded `reason_code`, and
contains no text. The client never copies another tab, a hidden result, an
internal candidate or the newest revision discovered during the clipboard
operation. The clipboard command snapshots the descriptor and payload under
that same revision fence, then announces the copied layer (`Итоги` or
`Расшифровка`).

## Ensure/generate missing type

`POST /cabinet/meetings/{meeting_id}/summaries/{template_key}/ensure`

Request:

- CSRF/auth context;
- idempotency key;
- source/template version expectation where required.

Response:

- existing ready revision, or one active attempt status;
- no accept/reject actions.

The same idempotency key with the same durable request identity returns the original attempt/result after a lost response. A different identity under the same key returns a stable conflict and never dispatches.

In the Feature 196 interaction contract, selecting a missing type is the one
explicit user intent that calls this endpoint. There is no second `Generate`
confirmation; ordinary GET/read remains side-effect free.

`availability_state=retired|unavailable`, `source_state=transcript_failed|empty|not_ready` and `generation_state=ambiguous` deny a new ensure with their exact bounded reason. Only a proven-safe state may expose `retry_safe`.

## Refresh type

`POST /cabinet/meetings/{meeting_id}/summaries/{template_key}/refresh`

Request includes:

- idempotency key;
- `expected_current_outcome_set_id`;
- exact chosen template version and generation options allowed by promoted config.

Response keeps current result, source freshness and attempt status separate. A successful worker publication changes the slot; the client observes it through bounded polling/event update.

Every response/event carries `meeting_id`, `template_key`, `current_outcome_set_id` and bounded `attempt_id`. A valid event may update the cached availability/status for its own type even when that type is not visible. It may repaint visible content, move the selector or update the remembered successful type only when meeting, selected type and the latest client-owned presentation-intent version still match. An event for type A can never repaint type B, and a stale event cannot override newer navigation or selection intent.

The summary snapshot and every summary state event additionally carry a positive
`state_version` scoped to `(meeting_id, template_key)`. The version starts at 1
for the first durable slot/attempt state and increments exactly once for each
committed client-visible state transition; it is never derived from wall-clock
time or an attempt ID. A summary event has exactly one opaque non-zero
`event_id`, `schema_version=1`, the meeting/type/attempt identity above, the
`state_version`, current result/generation/source/catalog state and the bounded
capability/error fields. The server sends
`ETag: "sum-{meeting_id}-{template_key}-v{state_version}"` with a private
no-store response; `If-None-Match` may return `304` without content. The client
ignores an event with `state_version <= cached_state_version`, and a detected
gap (`state_version > cached_state_version + 1`) triggers one authoritative
read before applying later events. Refetch is scoped to the same meeting/type
and cannot repaint another active tab.

## Regenerate transcript in the selected language (Feature 197)

`POST /cabinet/meetings/{meeting_id}/transcript/regenerate`

This is the only public transcript-language regeneration command. Cookie-based
requests require authenticated same-origin session plus valid CSRF token;
workspace/meeting authorization is checked before any durable job or provider
egress. The strict request has exactly:

```text
schema_version = 1
language_selection = one of:
  { mode: explicit, language_tag: canonical BCP-47 ASCII string, 1..255 bytes }
  { mode: auto_detect }
expected_source_revision = opaque current source revision
access_policy_epoch = non-negative signed-int64, 0..2^63-1
deletion_epoch = non-negative signed-int64, 0..2^63-1
transcription_policy_epoch = non-negative signed-int64, 0..2^63-1
idempotency_key = 16..200 ASCII bytes
predecessor_job_id = UUID | null
```

`language_selection` is the only client-facing language shape. `auto_detect` is
resolved once at the authenticated command boundary by the pinned transcription
language detector and promoted allowlist; a low-confidence or unsupported
resolution returns `transcript_language_auto_detect_unresolved` and creates no
job. The durable job and its business identity always store the resolved
canonical `language_tag`, never the UI label `Auto-detect` and never an
unresolved sentinel. The response exposes both the requested mode and the
resolved tag so the UI can explain what will be reprocessed.

The server validates/canonicalizes the resolved `language_tag` under one pinned BCP-47
registry/normalization version and the promoted transcription-provider allowlist;
underscore forms, unknown/unsupported mappings and lossy client normalization
fail before job creation. The durable request identity is the canonical tuple
`workspace + meeting + resolved language_tag + expected_source_revision + access/deletion/
transcription-policy epochs + transcription-pipeline version + BCP-47
normalization/allowlist versions`. Its `request_identity_hash` is the business
dedupe identity only: it excludes the idempotency key, `job_id`, retry lineage,
Temporal Workflow/Run IDs and provider IDs. Each durable execution instead owns
one immutable random UUID `job_id`.

Same key and byte-equal identity returns the exact job originally bound to that
key; same key with a different identity is
`transcript_regeneration_idempotency_conflict`; a different key for an equivalent
non-terminal identity joins that job. A stale source or epoch returns conflict
and creates no work. The first job has `retry_ordinal=0` and null
`predecessor_job_id`. A successor requires a fresh idempotency key, names the
immediate predecessor, keeps the same business identity hash, receives
`retry_ordinal=predecessor.retry_ordinal+1` and a new `job_id`, and may be
reserved only after the locked predecessor is terminal `failed` with durable
positive safe-retry proof and every source/access/policy/deletion fence is still
fresh. `ambiguous`, `succeeded` and `invalidated` jobs cannot have a successor;
one predecessor can reserve at most one direct successor.

`expected_source_revision` is the exact positive revision from
`MeetingCanonicalSourcePointer`, not a client-derived latest result/version or
timestamp. The server also compares that pointer's source-basis hash inside the
reservation transaction.

The response is one `TranscriptRegenerationJobV1` with exact `job_id`,
`request_identity_hash`, `retry_ordinal`, nullable `predecessor_job_id` and
`successor_job_id`, the original `language_selection`, resolved
`language_tag`, `expected_source_revision`, monotonic
`state_version`, `state`, `created_at`, `updated_at`, conditional
`replacement_source_revision`, bounded `reason_code`, `retryable`, `next_action`
and bounded `poll_after_ms` while non-terminal. State is exactly `submitted |
sending | accepted | ambiguous | processing | succeeded | failed | invalidated`.
Legal transitions are:

```text
submitted → sending
sending → submitted             only with proof that no provider egress began
sending → accepted | ambiguous
sending → failed                only on definitive provider rejection
accepted → processing | succeeded | failed
ambiguous → accepted | processing | succeeded | failed   only by authoritative reconciliation
processing → succeeded | failed
any non-terminal → invalidated  when a bound source/access/policy/deletion fence changes
```

The immutable provider correlation/idempotency ID is generated and committed on
the job before `submitted → sending` or any provider I/O. Every allowed submit
uses that same ID. The provider contract must support either authoritative
authenticated lookup by that correlation/stable returned operation identity or
a signed callback carrying it; without such a reconciliation capability the
provider is unavailable for this command. A provider-issued job ID may be added
after acceptance, but it never substitutes for the pre-egress correlation ID.

The Temporal submit Activity has `maximum_attempts=1`. Temporal timeout, worker
loss and generic transport retry policy cannot resubmit it. The orchestration may
schedule another submit Activity for the same job only after a committed typed
result proves that no byte/request left GRAF; it reuses the same provider
correlation ID. A definitive authenticated rejection proves the provider did not
accept an operation and commits `sending → failed`; timeout, connection loss,
malformed response or any uncertain acceptance commits `ambiguous` instead.

Temporal Workflow ID is derived from immutable `job_id`, never from reusable
`request_identity_hash`, and starts with
`WorkflowIdReusePolicy=REJECT_DUPLICATE`. An already-started response causes the
starter to re-read that exact database job; it is not permission to start or
join a different execution. A proven-safe successor therefore has a new job and
Workflow ID while preserving its explicit business lineage.

`ambiguous` is wait-only and never retryable. Timeout/connection loss after
possible provider acceptance cannot create another provider submission; a
server reconciler uses the exact provider operation identity, signed callback or
authoritative status lookup. `failed` exposes `retry_safe` only with positive
no-egress or terminal-provider proof and fresh request fences. Provider IDs,
errors and transcript content are never returned to the browser.

### Recover and poll transcript regeneration

The side-effect-free recovery surface is:

```text
GET /cabinet/meetings/{meeting_id}/transcript/regenerations/current
GET /cabinet/meetings/{meeting_id}/transcript/regenerations/{job_id}
```

Both routes require the same authenticated meeting/workspace authorization as
the POST and perform authorization/deletion checks before job lookup, ETag
comparison or conditional response. Missing meeting, inaccessible meeting,
cross-workspace/cross-meeting `job_id`, deleted/deleting meeting and missing job
return the same bounded `404 transcript_regeneration_not_found` shape with no
ETag. An authorized `current` read returns the unique non-terminal source-
replacement job for that meeting/current source, or `204` when none exists. A
by-ID read returns that exact authorized job, including a terminal lineage node;
neither read dispatches, retries, reconciles or mutates work.

`state_version` is a positive signed-int64 in `1..2^63-1`, starts at `1` and
increases monotonically in the same transaction
as every client-visible state, reason, retry proof/action, successor or
replacement-revision change. Exhaustion fails closed rather than wrapping. A
`200` response carries
`ETag: "trj-{job_id}-v{state_version}"`, `Cache-Control: private, no-store` and
the typed `TranscriptRegenerationJobV1`. Only after authorization, an exact
`If-None-Match` returns `304` with no body. Poll cadence comes from bounded
`poll_after_ms`; the client does not derive it from provider state.

The committed event is `TranscriptRegenerationJobChangedV1` with exactly
`schema_version`, opaque `event_id`, `meeting_id`, `job_id`, `state_version`,
`state`, conditional `replacement_source_revision`, bounded `reason_code`,
`retryable`, `next_action` and nullable bounded `poll_after_ms`. It is published
only to an already authorized meeting channel after commit and contains no provider ID,
error body or transcript. Clients ignore versions at or below the cached value;
a version gap, reconnect or navigation recovery performs the authenticated GET
and cannot issue another POST. Access loss or deletion closes the subscription
without disclosing whether another job exists.

Browser mapping is deterministic: `submitted|sending|accepted|processing|
ambiguous` shows transcript `preparing` with `next_action=wait`; `failed` shows a
calm language-correction error and only a proven-safe retry; `invalidated` maps
to the current access/deletion/source state; `succeeded` returns the exact new
source revision and causes saved summary types to report `stale` plus their own
bounded replacement state. The old transcript remains visible until the
replacement transaction commits; a failed/ambiguous job never relabels it as the
new language.

Successful replacement is one server transaction that locks and revalidates
the job, current source pointer, access/deletion/policy epochs and replacement
artifact; creates or reuses exactly one immutable canonical source revision;
moves the current-source pointer; marks only active saved old-source summary
slots stale; and creates/coalesces at most one replacement DispatchIntent per
saved, active, available type, persisted default/current type first. It never
generates an unsaved catalog type or a retired type. A retired saved result stays
stale/read-only. If another source revision won first, the job is invalidated and
its provider result cannot overwrite or fan out from that newer source.

## Feature 183 share/export compatibility

Existing summary egress resolves the slot marked `is_meeting_default`, including its `default_resolution_source`, opaque `default_resolution_version` and timestamp. Feature 197 writes that marker before automatic dispatch. Only a legacy meeting with no marker may run the documented versioned workspace resolver once and persist the selected marker inside the egress transaction. The resolver never consults the requesting user's presentation preference or dynamic personal default, and a missing/retired default fails honestly. The exact current outcome and source basis are verified and the `template_key`/`outcome_set_id` pair is written to the share grant or export manifest in the same transaction that creates/activates that artifact. A refresh that commits before this linearization point may be pinned; a refresh after it never changes the artifact. Latest attempt/row and another available type are forbidden fallbacks. Explicit arbitrary-type selection is added only by Feature 203.

## Compatibility endpoints

Existing candidate preview/accept/reject endpoints become deprecated implementation surfaces. Feature 183 removes all HTML/HTMX links and rejects ordinary cabinet access with a stable gone/forbidden response; automatic publication uses the internal service directly. Physical route removal follows after caller/source scans prove zero compatibility use.

## Stable error reasons

- `summary_type_not_found`
- `summary_type_unavailable`
- `summary_type_retired`
- `summary_generation_in_progress`
- `summary_generation_blocked`
- `summary_generation_deferred`
- `summary_generation_ambiguous`
- `summary_source_revision_stale`
- `summary_source_not_ready`
- `summary_source_empty`
- `transcript_generation_failed`
- `summary_revision_conflict`
- `summary_result_invalid`
- `summary_prompt_revoked`
- `summary_dependency_unavailable`
- `meeting_deleting`
- `summary_current_revision_missing`
- `summary_default_missing`
- `summary_legacy_state_ambiguous`
- `transcript_regeneration_idempotency_conflict`
- `transcript_regeneration_source_conflict`
- `transcript_language_invalid`
- `transcript_language_unsupported`
- `transcript_regeneration_ambiguous`
- `transcript_regeneration_invalidated`
- `transcript_regeneration_not_found`
- `transcript_regeneration_retry_not_safe`
- `transcript_regeneration_provider_reconciliation_unavailable`

Terminal attempt recovery additionally uses the closed reason codes
`no_eligible_items`, `no_selected_items`, `focus_no_supported_topic`,
`focus_ambiguous` and `focus_topic_catalog_capacity_exceeded`. They follow the
public recovery mapping above and are not substituted with generic errors.

Error bodies contain no transcript, prompt, raw model response or provider error body.
