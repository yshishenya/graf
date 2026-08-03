# Contract: transcript and summary recovery

This slice changes the effective state returned by existing cabinet routes; it
does not add an endpoint or change the export file schema.

## Existing capability contract

`GET /api/v1/cabinet/meetings/{meeting_id}/content-export-capabilities` and the
existing content-export POST must agree on one effective decision:

- owner + ready imported transcript + accepted/current matching outcome:
  transcript and summary are `available` under an implicit owner-only policy;
- non-owner or explicit disabled override: the corresponding artifact is
  denied/owner-only and the export route remains blocked;
- missing, stale, deleted or mismatched result: the route remains fail-closed;
- accepted outcome present: a new baseline/candidate never changes the exported
  current result.

The existing package state uses the same owner-only effective policy and only
includes artifacts that are already exportable.

## Internal validation contract

`validate_outcome_result()` continues to return the closed outcome schema. For a
known pinned segment ID, it canonicalizes the returned source sequence to the
server mapping. Unknown IDs, missing fields, invalid sequence types and
out-of-range values raise a validation error.

## Maintenance contract

`apps/server/scripts/reconcile_initial_outcomes.py` is metadata-safe by default.
It prints counts and state identifiers only. `--execute` is required for a
bounded repair and invokes the same fenced outcome service used by processing;
it never accepts an AI candidate, changes policy, or changes the meeting
lifecycle status.
