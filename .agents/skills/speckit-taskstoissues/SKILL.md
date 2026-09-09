---
name: "speckit-taskstoissues"
description: "Convert existing tasks into actionable, dependency-ordered GitHub issues for the feature based on available design artifacts."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/taskstoissues.md"
---


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks-to-issues conversion)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_taskstoissues` key
- If the YAML cannot be parsed or is invalid, STOP with a blocking configuration error; do not skip configured hooks
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** interpret the `condition` expression yourself:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If an optional hook defines a non-empty `condition`, skip it and leave evaluation to HookExecutor
  - If a mandatory hook defines a non-empty `condition`, invoke HookExecutor and wait for its result; if HookExecutor is unavailable, STOP with a blocking error instead of continuing
- When constructing command invocations from hook command names, replace dots (`.`) with hyphens (`-`). For example, `speckit.git.commit` → `$speckit-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook. Before invocation, classify the hook as read-only or state-changing. Commit, publish, deploy, destructive, or other state-changing hooks require explicit user confirmation at this point even when `optional: false`; without confirmation, STOP instead of executing them.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Closeout mode

When arguments explicitly contain `closeout` and the repository provides
`scripts/validate-issue-closeout.py`, reconcile existing issues instead of running
the creation Outline below. Read the project's tracker policy and current feature
spec/plan/tasks. This mode creates no new issues and does not declare the feature
complete while mandatory acceptance remains open.

1. Re-read live issue bodies/comments/state and establish ownership from exact
   task links plus canonical title/body fields. A checked task is a candidate,
   not proof of every issue acceptance criterion. Do not infer ownership from
   only a feature/task number or ordinary references.
2. Verify the actual merged implementation, every original acceptance criterion,
   required review/runtime/release evidence and the exact tested SHA. If merge,
   release or manual acceptance is still pending, keep the issue open and report
   the concrete missing requirement. Never turn missing evidence into cancellation.
3. For a fully satisfied issue, prepare the detailed Russian closure comment
   required by tracker policy, including PR number, explicit PR SHA,
   `governance-fast: PASS` run URL and, when required, Candidate SHA and
   `release-full: PASS` URL. First validate a temporary issue JSON containing that
   proposed comment with `scripts/validate-issue-closeout.py --issue-json <path>
   --tasks <tasks.md> --expected-sha <SHA> --repo <owner/repo> --verify-live`;
   add `--require-release-full` for release-gated acceptance. A nonzero result
   blocks closing. The command verifies metadata and live PR/runs; human/runtime
   acceptance must also be evidenced, never inferred from a green run.
4. Within the user's authorized tracker scope, re-read state/comments before
   writing, add the approved-by-evidence comment only if absent, export the actual
   issue again and repeat validation, then close as completed and verify state.
   If GitHub already auto-closed it, validate its evidence and add the missing
   comment; reopen when mandatory evidence/tasks are incomplete. For explicitly
   superseded work use NOT_PLANNED with the actual replacement, not fabricated
   completed tasks. Do not duplicate comments on retry; stop on rate limits and
   preserve a resumable list of remaining issue numbers.
5. Close the umbrella last, only after live feature-mode validation with
   `--repo --feature --umbrella --tasks --expected-sha --allow-open-umbrella`
   (and the release flag when required). Verify again without
   `--allow-open-umbrella`. If unresolved criteria remain, the result is
   `tracker pending`, even when implementation itself is complete.
6. Run the Post-Execution Checks below and report exact closed/already-closed/
   remaining issue numbers with reasons. Do not continue into the creation Outline.

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
1. **IF EXISTS**: Load `.specify/memory/constitution.md` for project principles and governance constraints.
1. From the executed script, extract the path to **tasks**.
1. Get the Git remote by running:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

1. **Fetch existing issues for deduplication**: Before creating anything, build the set of task IDs you are about to process from `tasks.md` (each is a `T` followed by **at least** three digits, e.g. `T001` — `$speckit-converge` assigns new IDs with `T{M+1:03d}`, which is a floor rather than a cap, so once a file has more than 999 tasks the IDs are four digits or longer). Then use the GitHub MCP server's `list_issues` tool to look for issues that already cover those IDs. Do not pass a `state` value, since omitting it makes the tool return both open and closed issues. Request `perPage: 100` to keep the number of calls down, and since the tool uses cursor-based pagination, request pages with the `after` parameter (using the `endCursor` from the previous response). For each issue, establish task ownership only from a canonical title containing `T###:` or an explicit body field such as `Spec Kit task IDs: T001, T002`; ordinary dependency, context, or link mentions do not establish ownership. Mark open ownership matches as covered. Track closed ownership matches separately: when `tasks.md` still has that task unchecked, verify closure and implementation evidence, then either reopen the issue with a Russian reconciliation comment or STOP and report the `tasks.md` mismatch when the closure is valid. Never create a duplicate while a closed match is unresolved. Deduplicate the task IDs before processing them. Stop paginating only when every unique task ID has an open owner or a reconciled closed owner, or when there are no more pages.
1. For each task in the list, use the GitHub MCP server to create a new issue in the repository that matches the Git remote. First read `docs/agent-guidance/github-issue-canon.md` when it exists. Under that project canon, construct its required feature/priority/area title, Russian outcome, body sections, labels, and traceability; the bare `T001: <description>` title is only a fallback for repositories without a project canon. Strip the leading task checkbox and optional `[P]`/`[US#]` markers before mapping the task. Iterate each unique task ID once and add a successfully created ID to the covered set before processing the next task.
   - **Skip** any task whose ID is already present in the set of existing issues from the previous step, and report it (for example, `T001 already has an issue, skipping`).
   - Only create issues for tasks that do not yet have a matching issue.

> [!CAUTION]
> UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL

## Post-Execution Checks

**Check for extension hooks (after tasks-to-issues conversion)**:
Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_taskstoissues` key
- If the YAML cannot be parsed or is invalid, STOP with a blocking configuration error; do not skip configured hooks
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** interpret the `condition` expression yourself:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If an optional hook defines a non-empty `condition`, skip it and leave evaluation to HookExecutor
  - If a mandatory hook defines a non-empty `condition`, invoke HookExecutor and wait for its result; if HookExecutor is unavailable, STOP with a blocking error instead of continuing
- When constructing command invocations from hook command names, replace dots (`.`) with hyphens (`-`). For example, `speckit.git.commit` → `$speckit-git-commit`.
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
    After emitting the block above you MUST actually invoke the hook and wait for it to finish before continuing. Run it the same way you would run the command yourself in this agent/session (the invocation may differ from the literal `{command}` id shown above, e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the block alone does not run the hook. Before invocation, classify the hook as read-only or state-changing. Commit, publish, deploy, destructive, or other state-changing hooks require explicit user confirmation at this point even when `optional: false`; without confirmation, STOP instead of executing them.
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently
