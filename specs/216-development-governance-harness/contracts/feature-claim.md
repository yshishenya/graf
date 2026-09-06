# Contract: Feature Claim and Preflight

## Inputs

- Feature description and requested slug.
- `origin/master` integration base.
- GitHub repository `yshishenya/graf`.

## Preconditions

- Git repository is available and remote matches the configured project.
- No uncommitted user changes are overwritten.
- GitHub access is available for a normal claim; offline mode is draft-only.

## Required behavior

1. Inspect local `specs/`, local/remote branches, visible GitHub issues and PRs.
2. Select a collision-free three-digit Feature ID.
3. Create or identify exactly one umbrella issue with the issue canon and
   `feature:<id>` label.
4. Create one branch and one spec directory using the same ID and slug.
5. Write `.specify/feature.json` only in the current worktree.
6. Return an agent context manifest with owner, SHA, risk lane and owned paths.

## Failure behavior

- On collision, fail with the conflicting refs/issues and do not create a
  branch or overwrite a spec.
- On GitHub outage, do not claim a fresh ID; allow only an explicitly labelled
  local draft with no merge/release eligibility.
- On a dirty worktree, report paths and stop before mutation.

## Invariants

- One active claim per Feature ID.
- Feature ID is never reused after closure.
- No mtime-based feature selection.
