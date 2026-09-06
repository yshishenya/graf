# Issue Closeout Contract

Before closing a task-backed issue:

1. `tasks.md` has `[X]` for every task named by the issue.
2. The PR or closeout record contains exact-SHA validation evidence and the
   correct `Fixes`/`Refs` relationship.
3. A Russian comment uses the required sections: what closed, why important,
   how checked, out of scope, Spec task and PR.
4. If GitHub already auto-closed the issue, add the comment immediately and
   reopen it if the task/evidence state is not complete.

An unchecked task, stale SHA, absent comment or missing evidence is a blocking
closeout gap, not a cosmetic documentation issue.
