# Contract: metadata-only repair evidence

Evidence is written atomically as UTF-8 JSON and contains schema version `1`,
operation and decision ids, exact source SHA, target boundary, timestamps,
revision/head results, backup/restore digests, two upgrade results, readiness
and representative API verdicts, component SHA map, and final status.

For a `dev-existing` probe, `database_probe` contains only `status`, a stable
`reason_code`, and the single `current_revision` when it was read successfully
(optionally a revision count for a multiple-revision block). It never contains
the database URL, credentials, command stderr, or query results from
application tables.

Evidence is valid only if all hashes refer to the same source SHA and the target
boundary is Dev. Any failed stage, interrupted command, changed HEAD, unknown
process identity or missing reviewer approval produces `blocked` or `failed`,
never `pass`.

Before issue or PR publication run a secret/path scanner. Evidence must contain
no credentials, signed URLs, raw audio, transcript text, user rows, or private
filesystem paths.
