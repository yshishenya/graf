# Data Model: Process Closeout And Issue Truth

## Feature claim

`feature_id`, `issue_number`, `branch`, `slug` and `source_sha`. The claim is
reserved by one open, labelled GitHub umbrella issue and mirrored in the local
shared claim file; `.specify/feature.json` is only the active worktree pointer.

## Task/issue link

`feature_id`, `task_id`, `issue_number`, `state`, `acceptance_status`,
`validation_evidence` and `pr_number`. Every executable task has one canonical
issue link; an issue may close only when all linked tasks and evidence are
complete.

## Closure evidence

The evidence record is metadata-only: exact tested SHA, required check URL,
focused commands, reviewer/owner identity, scope and a Russian closure comment.
It must never contain meeting content, raw audio or credentials.
