# Feature 099 Baseline

**Recorded**: 2026-07-14
**Validation lane**: significant/high-risk active Spec Kit slice

## Workspace anchor

- Worktree: dedicated clean 099 worktree (`$REPO_ROOT`).
- Branch: `codex/099-review-m4a-normalization`
- Feature anchor: `specs/099-review-m4a-normalization`
- `.specify/feature.json` resolves to the same feature directory.
- Base, initial HEAD and merge-base with `origin/master`:
  `ab818459467d11006e24575242236b5f7872d8e4`.
- The unrelated dirty detached worktree identified as `30ac` was inspected
  read-only and is excluded from every 099 write, stage, commit and cleanup
  operation.

## Workflow state

- Specify and three clarifications are complete.
- Plan, research, data model, four contracts and quickstart are complete.
- Requirement-quality checklists pass 80/80.
- `$speckit-analyze` passes with 42/42 FR and 22/22 SC covered.
- `tasks.md` contains 116 sequential executable tasks.
- GitHub task sync has 116 open `feature:099` issues, one per T001–T116; canon
  validation reports `OK`.
- No implementation commit exists and no 099 files are staged.

## Existing product boundaries verified

- `ingest/manifest.py` currently accepts only exact first-party and manual role
  sets; optional playback requires a scoped extension.
- `MediaRevision` and `TrackArtifact` own accepted source and artifact lineage.
- Current playback egress can fall back across stored audio roles; 099 must
  require a fully validated canonical playback artifact.
- MediaScribe processing already has a separate Temporal worker and task queue.
- Production compose currently runs that processing worker as root; 099 must
  either remove the override safely or retain it only with explicit evidence,
  while the new media worker is always non-root.
- The macOS app already emits an optional AAC-LC/48-kHz/mono playback candidate
  plus required accepted microphone/system sources. No native behavior change
  is planned.

## Initial commands

```text
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
git rev-parse HEAD origin/master
git merge-base HEAD origin/master
git status --short
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
```

## Explicit exclusions

- Feature 097 and its standalone Codex Security scan remain deferred and were
  not opened, resumed, failed, completed or written by this workflow.
- Feature 100 has not started.
- No production mutation, release, deploy, tag, PR or commit is authorized by
  this baseline.
