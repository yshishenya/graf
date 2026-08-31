# Research: CI merge queue и provenance release train

## R1 — Event-specific target identity

PR workflows expose a PR head SHA, merge queue validation is represented by
`merge_group` and its synthetic head SHA, and manual dispatch has no trusted
target without an explicitly supplied full SHA. One resolver must reject all
other cases.

## R2 — Concurrency and cancellation

`pull_request` and `workflow_dispatch` currently use different concurrency
namespaces. A canonical key must be derived from the logical target (PR number,
merge-group ID or explicit manual target), with `cancel-in-progress: true`.
Cancellation is terminal non-success, never a pass.

## R3 — Final cleanliness

Local CI checks the tree before tests, but tests/builds can create files
afterwards. The final receipt must re-check tracked and untracked drift after
artifact generation and allow only documented metadata-only evidence paths.

## R4 — Release provenance

Candidate freeze/validate/decide already binds exact source SHA and changelog
digest. A separate train manifest is needed for PR/Feature IDs, merge-group
receipts and the post-merge SHA.

## R5 — Portable boundary

Event identity, receipt schemas, stale validation and train templates are
generic. GRAF-specific signing, capture/privacy, Temporal/worker readiness and
production deployment gates remain project-local.

## R6 — Merge-group mapping

GitHub's merge-group event provides the synthetic target identity but may not
embed every pull request in the group. The workflow must resolve the mapping
from GitHub's authoritative merge-queue API using the group ID or synthetic SHA;
commit-message parsing is not an acceptable source of provenance. Missing or
ambiguous mapping is a terminal non-success state.
