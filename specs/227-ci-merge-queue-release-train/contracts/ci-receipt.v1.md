# CI Receipt Contract v1

The producer and validators exchange one metadata-only JSON object.

Required fields:

```text
schema_version
status
event_name
workflow
run_id
run_attempt
workflow_url
target_sha
base_sha
pull_request_numbers
merge_group_id
requested_sha
observed_sha_start
observed_sha_end
final_cleanliness
local_evidence_digest
started_at
finished_at
```

Rules:

- `target_sha`, `requested_sha`, `observed_sha_start` and
  `observed_sha_end` must be identical full hexadecimal SHAs for a pass.
- `status=passed` requires `final_cleanliness=pass` and a non-stale target.
- `cancelled`, `superseded`, `stale`, `ambiguous` and `failed` are terminal
  non-success values.
- `merge_group_id` is required for `event_name=merge_group`.
- `base_sha` is required for PR and merge-group events.
- A receipt must not contain command logs, credentials, private absolute paths,
  audio, transcript text or signed URLs.
