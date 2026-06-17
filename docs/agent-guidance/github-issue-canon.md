<!-- managed-by: github-issue-canon -->

# GitHub Issue Canon

This repository uses GitHub Issues as the execution backlog that mirrors Spec
Kit tasks. Every issue created manually, by an agent, or through
`$speckit-taskstoissues` must follow this canon unless the user explicitly asks
for a one-off scratch issue.

Project path:

```text
docs/agent-guidance/github-issue-canon.md
```

All issue titles, issue bodies, status comments, closure comments, and sync
notes must be written in Russian by default. Use simple, clear language that is
understandable to non-technical teammates, not only engineers.

## Title Format

Use this exact format:

```text
[{feature}][{priority}][{area}] {imperative outcome}
```

Examples:

```text
[012][P0][ingest/finalize] Reject mismatched artifact manifests before finalize
[012][P1][infra/compose] Fail closed on production dev defaults
```

Rules:

- `{feature}` is the three-digit Spec Kit feature number, e.g. `012`.
- `{priority}` is `P0`, `P1`, `P2`, or `P3`.
- `{area}` is a compact ownership/scope tag.
- The title states the desired outcome in imperative form.
- Do not use emoji, urgency words, all-caps shouting, or repeated punctuation.
- Do not prefix with `bug:`/`feature:` when the same meaning belongs in labels.

## Body Format

Use sections in this exact order.

```markdown
## Summary

One or two sentences describing what must become true.

## Context

- Feature: `012-server-ingest-foundation`
- Spec tasks: T119, T132
- Source: review / analyze / implementation / user report / production incident
- Gate: blocks PR / blocks deployment / follow-up / nice-to-have
- Related issues: #123, #124

## Problem

Concrete current behavior, gap, or risk. Explain why it matters.

## Confirmed Findings

- Observed fact or reviewed gap.
- Missing test/proof.
- Risk if left unresolved.

## Scope

In scope:
- ...

Out of scope:
- ...

## Acceptance Criteria

- [ ] Given ..., when ..., then ...
- [ ] ...

## Validation Required

- [ ] Test file or command.
- [ ] Contract/checklist/compose/manual smoke evidence.
- [ ] Documentation/status update if required.

## Implementation Notes

Constraints, important paths, and known traps. Keep this practical, not a full
design document.

## Links

- Spec:
- Plan:
- Tasks:
- Related:
```

## Labels

Use labels as metadata; do not duplicate all metadata in the title.

Required label families for Spec Kit issues:

- `feature:<number>`: e.g. `feature:012`
- `priority:P0`, `priority:P1`, `priority:P2`, or `priority:P3`
- `area:<name>`: e.g. `area:ingest`, `area:auth`, `area:infra`
- `gate:<name>` when applicable: `gate:pr-blocker`, `gate:deployment-blocker`
- `type:<name>`: `type:bug`, `type:hardening`, `type:docs`,
  `type:test-gap`, or `type:feature`

## Closing Rules

- Close an issue only when every acceptance criterion is met or explicitly
  marked not applicable with a reason.
- Use `Closes #123` in the PR description only when that PR fully closes the
  issue.
- Use `Refs #123` or `Part of #123` when a PR only contributes partial work.
- Do not close a security/privacy/durability issue without validation evidence
  recorded in the PR or the feature quickstart/status docs.
- When an issue maps to Spec Kit tasks, mark matching tasks `[X]` in `tasks.md`
  only after implementation and validation are complete.

## Automation And Spec Kit

- `$speckit-taskstoissues` must create issues using this canon.
- The `github-issue-canon` Spec Kit extension installs this file under
  `docs/agent-guidance/`, issue forms, labels, and validation hooks.
- Do not patch globally installed Spec Kit skills to enforce this rule; they may
  be overwritten by Spec Kit updates.
