# Contract: Meeting Outcomes Lifecycle

## Generation Trigger

Outcome generation may start when:

- a meeting has a latest accepted media revision;
- a latest processing result exists for that media revision;
- transcript status is `available`;
- meeting lifecycle and policy allow review;
- no current outcome set exists for the same workspace, meeting, media
  revision, processing result, and generator version.

Outcome generation must not start when:

- transcript is unavailable or failed;
- meeting is deleting/deleted/retention-blocked;
- workspace policy disables outcome generation;
- an unsafe prior result is still under operator review;
- a current generation attempt is already queued/running for the same input.

## Idempotency

Input identity:

```text
workspace_id
meeting_id
media_revision_id
processing_result_id
generator_version
```

The service must return or reuse the current outcome set/attempt for duplicate
requests with the same identity. A retry may supersede a failed/blocked/partial
attempt only when it creates a new attempt and preserves prior accepted output
until the new output is stored successfully.

## Failure And Timeout States

Safe failure reason examples:

- `outcomes_transcript_unavailable`
- `outcomes_transcript_empty`
- `outcomes_generation_timeout`
- `outcomes_dependency_unavailable`
- `outcomes_malformed_provider_output`
- `outcomes_unsafe_output`
- `outcomes_policy_blocked`
- `outcomes_deleted_meeting`

Failure metadata may include counts, latency, provider class, template/model
version, and reason code. It must not include meeting content.

## Deletion Contract

When a meeting deletion request is created or retention expires the meeting,
the lifecycle service must account for outcome rows as controlled meeting
content:

- outcome set rows;
- outcome item rows;
- generation attempts;
- provider traces if content-bearing traces ever become enabled;
- export/download copies only as post-egress limitations.

The user/admin copy must remain truthful: delete everywhere 2brain Rec controls,
not universal erasure outside controlled systems.

## RLS Contract

All new outcome tables are tenant-scoped and must:

- include `workspace_id`;
- enable and force RLS in Postgres migrations;
- use the existing content context expression for request/worker access;
- be listed in `RLS_DIRECT_WORKSPACE_TABLES`;
- be covered by migration/RLS tests and the local RLS validation boundary.

## Readiness Contract

The readiness model may close `notes-action-output` only when validation proves:

- stored category states/items exist for a processed owner meeting;
- web and embedded review show the same stored outcome truth;
- access denial exposes no content;
- deletion/lifecycle accounting includes outcomes;
- forbidden-content scans are clean;
- release/status docs state any limitations plainly.

If any of those are missing, the readiness output must keep the blocker open or
record an explicit owner-approved MVP deferral.
