# Data Model: GitHub Full CI

| Entity | Required fields | Invariants |
|---|---|---|
| Frozen candidate | `candidate_id`, `source_sha`, feature list, changelog digest | immutable; source SHA is current post-merge master |
| Component result | component name, requested/observed SHA, status, run ID | status is `passed` only when every component gate passed; no private content |
| Reservation | candidate ID, source SHA, workflow run ID | create-once; any existing reservation blocks a second authoritative run |
| Full evidence | lane, candidate ID, requested/start/end SHA, component SHAs, skipped gates, artifact digests | `lane=full`, `authoritative_full=true`, all component SHAs equal requested SHA, `skipped_gates=[]` |

## State transitions

```text
unreserved -> reserved -> components_passed -> authoritative_passed
                         \-> failed/cancelled (candidate invalid; no rerun)
```

The release operator may create a new candidate after a failed or interrupted
run. Existing candidates and evidence are never edited or overwritten.

## Canonical field mapping

`source_sha` in a frozen candidate is the same immutable value passed to the
workflow as `requested_sha`. Component `observed_sha_start` and
`observed_sha_end` must both equal `requested_sha`; any mismatch is stale and
cannot be attested. The aggregate `component_shas` map uses the component names
`server` and `macos_app`.

## Candidate state table

| State | Reservation | Evidence | Allowed next action |
|---|---|---|---|
| `unreserved` | absent | absent | start one Full CI run |
| `reserved` | present | absent | continue the original run only |
| `passed` | present | one authoritative record | attest/decide; never rerun |
| `failed`/`cancelled` | present | no-go or failed metadata | create a new candidate after correction |
| `invalid_input`/`stale_sha` | absent or not accepted | absent | correct inputs and create/dispatch a valid candidate |
