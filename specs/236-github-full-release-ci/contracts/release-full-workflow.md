# Contract: `release-full.yml`

## Inputs

- `candidate_id`: 1–160 characters matching `[A-Za-z0-9._:-]+`.
- `requested_sha`: exactly 40 hexadecimal characters and equal to the current
  post-merge `origin/master` SHA at reservation time.

## Required workflow behavior

1. Trigger is `workflow_dispatch`; it is not attached to `pull_request`.
2. Permissions are read-only (`contents: read`, `actions: read` when artifact
   lookup requires it).
3. Concurrency is keyed by candidate ID and never cancels an active run;
   different candidate IDs may run independently.
4. Reservation is published before component jobs and cannot be overwritten;
   a queued second run must fail immediately after the first reservation with
   `candidate_already_reserved`.
5. Ubuntu and macOS jobs checkout the exact requested SHA, macOS asserts
   `uname -m` is `arm64`, and both report their platform result without
   uploading logs or secrets.
6. Aggregation fails if a job fails, is cancelled, reports another SHA or skips
   a gate.
7. The only passed output is one `authoritative_full=true` evidence record;
   publication and deployment are out of scope.

## Constitution checkpoints

- Before research: exact SHA, read-only permissions, metadata-only artifacts and
  no-deploy boundary are checked against the constitution.
- After design: reservation, failure states, arm64 runner assertion, timeout
  bounds and `untouched` legacy classification are checked before implementation.

## Evidence contract

The aggregate record MUST pass `scripts/validate-ci-evidence.py` and MUST have:

```json
{
  "lane": "full",
  "authoritative_full": true,
  "status": "passed",
  "candidate_id": "rc-...",
  "requested_sha": "<40 hex>",
  "observed_sha_start": "<same SHA>",
  "observed_sha_end": "<same SHA>",
  "component_shas": {"server": "<same SHA>", "macos_app": "<same SHA>"},
  "skipped_gates": []
}
```
