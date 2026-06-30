# Audit Batch Contract

Every cleanup batch must provide the following evidence before it can be marked complete.

## Batch Header

- Batch ID and short name.
- Risk/validation lane.
- File and dependency scope.
- Explicit out-of-scope list.

## Candidate Evidence

Each candidate must include:

- Path and symbol/dependency name.
- Ponytail tag: `delete`, `stdlib`, `native`, `yagni`, `shrink`, or `retain`.
- Why the item exists today, if known.
- Caller/reference evidence.
- Framework/runtime exception check.
- Decision and rationale.

## Validation Evidence

Each completed batch must include:

- Focused command(s) for touched paths.
- Language/tooling command(s) for touched languages.
- Repository gate result when behavior, shared code, UX, operations, release readiness, or code paths changed.
- Failure notes and rerun evidence if a gate failed before passing.

## Retained Candidate Notes

Suspicious items retained for safety must include:

- Why the item looked removable.
- Why it was retained.
- What future evidence would make removal safe.

## Completion Rule

A batch is complete only when all included candidates have decisions, all required validation commands pass or have accepted documented skips, and retained high-risk candidates are listed.
