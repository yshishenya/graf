# Research: transcript-export-recovery

## Existing flow

- Cabinet transcript, summary and package actions all pass through
  `cabinet/egress.py`; the UI does not own a second permission decision.
- When no `meeting_artifact_policies` row exists, the resolver returns
  `disabled` for every artifact with `policy_source="meeting_default"`.
  Audio already translates that implicit value to `owner_only`, while content
  artifacts do not.
- A revision-scoped deterministic outcome currently receives a candidate ID and
  stays `candidate` until an owner accepts it. The existing service is already
  fenced by the latest accepted media revision, processing result and source
  hash.
- AI outcome validation already rejects unknown transcript segment IDs and
  malformed references. It rejects a known ID with a provider-emitted sequence
  that disagrees with the pinned transcript, even though the ID is sufficient
  to recover the canonical sequence.
- `review_status()` uses the imported processing result/workflow state. It can
  report a ready transcript while the immutable legacy `Meeting.status` remains
  `ingested_pending_processing`; changing that status would be an unrelated
  lifecycle mutation.

## Decisions

### 1. Resolve implicit content policies as owner-only

Reuse the audio policy rule for transcript, summary and package values when the
resolver source is `meeting_default` or `workspace_default`. Keep an explicit
`meeting_override` value unchanged, including `disabled`. This fixes the
missing-row regression without creating policy rows or changing shared access.

Rejected: making content `allowed` by default, because it would broaden
non-owner egress; writing a row for every meeting, because it would erase the
distinction between an implicit default and an explicit owner decision.

### 2. Publish only the first trusted baseline

Add an opt-in flag to the existing outcome reconciliation function. The trusted
processing import passes it, and the maintenance repair script can pass it for
an existing ready candidate. The service publishes only when
`meeting.current_outcome_set_id` is empty. Later revision-scoped baselines keep
the current candidate/review flow, and any accepted outcome remains immutable.

Rejected: globally auto-accepting all baseline service calls, because direct
manual/test paths and later source revisions would lose the existing review
boundary; adding a new outcome table or endpoint, because the current pointer
and candidate tables already model the transition.

### 3. Canonicalize a known source ID, reject unknown sources

When a source reference contains a known pinned segment ID, replace only its
sequence with the stored sequence before persisting the validated result. Keep
the existing checks for shape, integer/non-negative sequence and segment-ID
membership. This is a bounded repair of provider serialization, not permission
to cite arbitrary transcript text.

Rejected: accepting unknown IDs, inferring by position, or retrying indefinitely;
those choices weaken provenance and can turn an invalid AI response into a
false accepted summary.

### 4. Keep processing/readiness semantics unchanged

Use the already imported result and workflow state for readiness. Do not mutate
`Meeting.status` as part of this feature; a separate lifecycle transition owns
that field. Add regression evidence for the current dual-state behavior.

## Operational boundary

The maintenance command defaults to metadata-only dry-run and requires
`--execute` for writes. This task does not run it against production. A later
approved rollout can repair the affected meeting or a bounded eligible set and
verify only identifiers, states and counts.
