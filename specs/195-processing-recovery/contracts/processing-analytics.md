# Contract: Processing Recovery Analytics

**Feature**: `195-processing-recovery`
**Status**: design-only metadata contract; this file does not enable a
provider, add a runtime writer, or change processing behavior.

## Purpose and boundary

This contract turns the Feature 195 recovery outcomes into measurable,
metadata-only rollups. It is intentionally narrower than the processing
workflow: it records bounded lifecycle outcomes after the server has already
decided the authoritative state. It does not copy provider responses, raw
errors, request bodies, transcript/audio material, or user/meeting identifiers.

The unit sent to a future analytics sink is an aggregate rollup for one
`window` + `event_name` + `surface` + bounded dimension set. `count` is the
number of server-side milestone occurrences in that group. The occurrence key
used to make a milestone idempotent remains an internal implementation detail;
it is never exported as an event field.

Only the server may emit processing lifecycle events. A browser or embedded
desktop surface is recorded as the bounded `surface` dimension for an action or
projection observation; neither client talks to a provider. The
`contract_test` surface is validation-only and is excluded from production KPI
denominators.

## Aggregate envelope

The machine-readable contract is
[`processing-analytics.schema.json`](processing-analytics.schema.json).
Every record contains exactly:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `1`; additive schema changes require a new version. |
| `event_name` | One of the events below; lower snake case and stable. |
| `window` | `hour` or `day`; rollup interval, not a user/session identifier. |
| `window_started_at`, `window_ended_at` | UTC ISO-8601 timestamps for the rollup window. |
| `surface` | `server`, `web_list`, `web_detail`, `embedded_desktop_detail`, or `contract_test`. |
| `count` | Positive integer aggregate count. |
| `dimensions` | Event-specific bounded enums/booleans only. |

The envelope has `additionalProperties: false`. Dimensions are event-specific;
an event cannot silently acquire a field from another event's allowlist.

## Event catalog

| Event | Emit when | Surface | Required dimensions | Grain and KPI use |
| --- | --- | --- | --- | --- |
| `processing_attempt_started` | A processing attempt is admitted to the authoritative GRAF lifecycle. | `server` | `attempt_kind`, `media_size_bucket`, `track_mode` | One per logical attempt; denominator for first-result and recovery rates. |
| `processing_first_usable_transcript` | Transcript and same-attempt, non-empty diarization are both available under the current deletion fence. | `server` | `latency_bucket`, `attempt_kind`, `media_size_bucket`, `track_mode`, `summary_state_at_ready`, `playback_state_at_ready` | One first milestone per eligible media revision; numerator and latency distribution for first usable transcript. |
| `processing_retry_scheduled` | A retryable state creates a durable next-attempt schedule or bounded fallback. | `server` | `retry_reason`, `schedule_source`, `delay_bucket`, `retry_count_bucket` | One per retry schedule generation; denominator for retry recovery and timer-source diagnostics. |
| `processing_retry_completed` | A scheduled retry slot reaches a bounded outcome. | `server` | `retry_outcome`, `attempt_kind`, `latency_bucket`, `same_key_reused`, `new_attempt_created` | One per retry slot; recovery, terminal and duplicate-prevention outcomes. |
| `processing_reconciliation_completed` | An unknown outcome is reconciled without exporting the original request or provider payload. | `server` | `reconciliation_outcome`, `attempt_kind`, `latency_bucket` | Same-key safety and support-escalation diagnostic. |
| `processing_manual_check_requested` | A user action reaches the server command boundary. | `web_detail` or `embedded_desktop_detail` | `request_result`, `same_job_check` | One per command result; accepted, duplicate-suppressed and stale-command rate. |
| `processing_manual_check_completed` | The one claimed manual check returns a safe lifecycle result. | `web_detail` or `embedded_desktop_detail` | `claim_result`, `check_outcome`, `latency_bucket`, `timer_superseded` | One per claimed check; execution and value-recovery rates. |
| `processing_terminal_outcome` | The attempt is confirmed terminal and no automatic countdown remains. | `server` | `terminal_category`, `next_action`, `artifact_preserved` | Terminal actionability and artifact-preservation guardrail. |
| `processing_support_handoff` | GRAF offers or records a support path for a case that cannot safely self-recover. | `server`, `web_detail`, or `embedded_desktop_detail` | `handoff_reason`, `handoff_state`, `artifact_preserved` | Handoff offer/completion and no-dead-end rate. |
| `processing_surface_parity_observed` | A contract fixture observes the same authoritative projection on one required surface. | `web_list`, `web_detail`, or `embedded_desktop_detail` | `fixture_class`, `parity_result`, `projection_contract_version`, `mismatch_reason` when mismatched | Surface parity pass rate; validation-only unless a later approved rollup writer exists. |

### Bounded dimensions

These values are deliberately coarse. Adding a new value requires a contract
review because a free-form provider code, title, path, identifier, or error
detail must not become a dimension.

| Dimension | Allowed values |
| --- | --- |
| `attempt_kind` | `initial`, `automatic_retry`, `manual_check`, `same_key_reconciliation`, `worker_resume` |
| `media_size_bucket` | `under_10mb`, `10mb_100mb`, `100mb_1gb`, `over_1gb`, `unknown` |
| `track_mode` | `single`, `dual`, `unknown` |
| `latency_bucket` | `under_30s`, `30s_2m`, `2m_5m`, `5m_15m`, `15m_30m`, `30m_2h`, `over_2h`, `unknown` |
| `summary_state_at_ready`, `playback_state_at_ready` | `not_requested`, `queued`, `running`, `available`, `failed`, `unavailable`, `unknown` |
| `retry_reason` | `result_not_ready`, `temporary_unavailable`, `transport`, `bounded_fallback`, `deadline_window`, `unknown` |
| `schedule_source` | `external_hint`, `server_fallback`, `manual_override`, `unknown` |
| `delay_bucket` | `under_30s`, `30s_2m`, `2m_15m`, `15m_1h`, `over_1h`, `unknown` |
| `retry_count_bucket` | `first`, `second`, `third_plus`, `unknown` |
| `retry_outcome` | `first_usable_transcript`, `artifact_progress`, `still_retryable`, `terminal`, `support_handoff`, `unknown` |
| `reconciliation_outcome` | `same_key_job_confirmed`, `same_key_conflict_blocked`, `no_safe_linkage`, `support_handoff` |
| `request_result` | `accepted`, `already_in_flight`, `stale_schedule`, `duplicate_suppressed`, `not_safe` |
| `same_job_check` | Boolean; true only means the command was scoped to the existing logical job, not that a new upload occurred. |
| `claim_result` | `claimed_once`, `already_in_flight`, `stale_noop`, `duplicate_suppressed` |
| `check_outcome` | `first_usable_transcript`, `artifact_progress`, `still_retryable`, `terminal`, `support_handoff`, `unknown` |
| `timer_superseded` | Boolean; records whether the pending schedule was invalidated by the claimed command. |
| `terminal_category` | `invalid_input`, `unsupported_media`, `processing_failure`, `deadline_exhausted`, `configuration`, `deletion_closed`, `unknown` |
| `next_action` | `new_attempt`, `contact_support`, `operator_action`, `none` |
| `artifact_preserved` | Boolean; only says that an already available safe artifact remained available. |
| `handoff_reason` | `terminal_processing`, `unknown_outcome`, `deletion_pending`, `configuration`, `no_safe_retry` |
| `handoff_state` | `offered`, `accepted`, `submitted`, `unavailable` |
| `fixture_class` | `transcript_pending_diarization`, `transcript_ready_summary_running`, `retryable_waiting`, `manual_in_flight`, `terminal_support`, `deletion_pending` |
| `parity_result` | `match`, `mismatch` |
| `projection_contract_version` | Bounded version such as `processing-status-v1`; no deployment or user identifier. |
| `mismatch_reason` | `missing_field`, `stale_timestamp`, `different_action`, `visibility_mismatch`, `independent_retry`, `unknown`; required only for `parity_result=mismatch`. |

## KPI definitions

All rates use aggregate `count` values and are calculated for the same time
window and bounded cohort dimensions. `contract_test` observations are never
mixed with production lifecycle events.

### First usable transcript

**`first_usable_transcript_rate`**

```text
sum(processing_first_usable_transcript.count)
/
sum(processing_attempt_started.count where attempt_kind=initial)
```

The numerator is emitted only after transcript plus confirmed diarization is
visible for the same attempt/revision and the current deletion fence passes.
The event is deduped at the server milestone boundary, so repeated refreshes,
polls, imports, or surfaces do not multiply it. Feature target anchor:
`SC-007` requires at least 95% of the acceptance workload to reach this
milestone.

**`time_to_first_usable_transcript`**

Report the distribution of `latency_bucket` on
`processing_first_usable_transcript`. The primary operational cut is:

```text
first_usable_transcript_within_5m
= sum(count where latency_bucket in {under_30s, 30s_2m, 2m_5m})
  / sum(processing_attempt_started.count where attempt_kind=initial)
```

The contract intentionally reports a bucket, not a meeting-level timestamp or
raw duration. A later dashboard may show bucketed p50/p95; this design slice
does not invent a latency target that Feature 195 has not approved.

`summary_state_at_ready` and `playback_state_at_ready` are guardrail
dimensions: summary or playback being `running`, `failed`, or `unavailable`
must not suppress the first usable transcript milestone.

### Retry recovery

**`retry_recovery_rate`**

```text
sum(processing_retry_completed.count
    where retry_outcome=first_usable_transcript)
/
sum(processing_retry_scheduled.count)
```

The grain is a retry schedule generation, not a raw provider request. Use
`retry_outcome=artifact_progress` as a separate diagnostic; it is not counted
as first usable recovery until the transcript+diarization condition is met.
Feature target anchor: `SC-006` requires at least 95% of recoverable transient
failures to reach a usable result without support handoff or user re-upload.

**`retry_resolution_rate`**

```text
sum(processing_retry_completed.count
    where retry_outcome in {first_usable_transcript, terminal, support_handoff})
/
sum(processing_retry_scheduled.count)
```

This detects retry loops that neither recover nor finish in an actionable
state. `still_retryable` must remain visible as an unresolved backlog bucket,
not be counted as success.

**`same_key_reconciliation_rate`**

```text
sum(processing_reconciliation_completed.count
    where reconciliation_outcome=same_key_job_confirmed)
/
sum(processing_reconciliation_completed.count)
```

`same_key_conflict_blocked` and `no_safe_linkage` stay visible as safety
outcomes. No metric may infer a duplicate or a new upload from a missing event.

### Manual check

**`manual_check_execution_success_rate`**

```text
sum(processing_manual_check_completed.count)
/
sum(processing_manual_check_requested.count where request_result=accepted)
```

For this metric, a completion is successful when the one claimed check returns
any safe lifecycle outcome (`first_usable_transcript`, `artifact_progress`,
`still_retryable`, `terminal`, or `support_handoff`). An exception or lost
claim is not silently converted into a completion.

**`manual_check_value_recovery_rate`**

```text
sum(processing_manual_check_completed.count
    where check_outcome=first_usable_transcript)
/
sum(processing_manual_check_requested.count where request_result=accepted)
```

This is the user-value slice of manual checks. It is reported separately from
execution success so a correct terminal/support response is not mislabeled as
a usable transcript.

**`manual_duplicate_suppression_rate`**

```text
sum(processing_manual_check_requested.count
    where request_result in {already_in_flight, stale_schedule, duplicate_suppressed})
/
sum(processing_manual_check_requested.count)
```

The acceptance guardrail is 100% suppression of a second operation for duplicate
clicks, two tabs, refresh retries, or a timer that wakes after the manual claim
(`SC-004`). A high rate can still indicate a UX problem, so it is a guardrail,
not a success KPI by itself.

### Terminal and support handoff

**`terminal_actionability_rate`**

```text
sum(processing_terminal_outcome.count where next_action != none)
/
sum(processing_terminal_outcome.count)
```

Every confirmed terminal state must have an explicit next action or an explicit
operator action. Terminal outcomes must not carry a retry countdown. The
`artifact_preserved` dimension is a guardrail that checks that an available
transcript/diarization artifact was not hidden by an unrelated terminal
failure.

**`support_handoff_completion_rate`**

```text
sum(processing_support_handoff.count where handoff_state in {accepted, submitted})
/
sum(processing_support_handoff.count where handoff_state=offered)
```

`unavailable` is an explicit failure bucket and must leave a copyable,
metadata-only support fallback. The metric does not claim that an external
support system accepted a report unless GRAF has an explicit `accepted` or
`submitted` state.

### Surface parity

**`surface_parity_pass_rate`**

```text
sum(processing_surface_parity_observed.count where parity_result=match)
/
sum(processing_surface_parity_observed.count)
```

The denominator must cover every required fixture class on each of
`web_list`, `web_detail`, and `embedded_desktop_detail`. The release contract
is 100% matching values for artifact availability, retry class, server next
attempt, manual action, in-flight state, and deletion-safe visibility. A
`mismatch` is a blocking validation finding, not a user event to hide in an
average.

## Retention, deletion, and ownership truth

- This slice defines `server_aggregate_only` semantics. It does not select or
  enable PostHog, Yandex, or another provider.
- The proposed retention category is `processing_aggregate_events`, with the
  existing 90-day minimum baseline and GRAF-controlled purge of aggregate rows.
- No user-level deletion claim is made for an already aggregated count. Reports
  must disclose that aggregate-only historical counts cannot be reconstructed
  to a meeting.
- A lifecycle event is eligible only after the current GRAF deletion fence is
  checked. A late import, stale Temporal activity, or deletion-epoch mismatch
  emits no first-result, retry-success, terminal, or surface-parity milestone.
- Support handoff dimensions remain categorical. They do not contain support
  ticket identifiers, request identifiers, raw error text, or copied payloads.
- `contract_test` records are synthetic validation evidence, not production
  telemetry, and must be excluded from operational dashboards.

## Implementation boundary for a later slice

This contract is intentionally sufficient for later implementation tasks T046
and T047, but it does not implement them. A future runtime change must prove,
before enabling collection, that:

1. events are generated from the authoritative PostgreSQL projection, not from
   client guesses or raw provider responses;
2. each milestone has an idempotent internal occurrence boundary;
3. the allowlist and strict schema are enforced before persistence/egress;
4. deletion-fenced writes cannot emit a late success event; and
5. the focused contract tests in
   [`processing-analytics-tests.md`](../validation/processing-analytics-tests.md)
   pass without adding provider or content fixtures.
