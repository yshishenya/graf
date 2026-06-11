# Legacy Linear Note: 015 MediaScribe Processing Pipeline

**Date**: 2026-06-11
**Feature**: `015-mediascribe-processing-pipeline`

## Current Decision

Linear is no longer part of the required workflow for this repository.

For `015`, this means:

- Missing Linear issues are not a blocker.
- Linear sync does not need to be completed before feature closure.
- Existing Linear references from earlier runs are legacy references only.
- `tasks.md` and GitHub issues remain the authoritative implementation and
  external-tracking evidence.

## Historical State

- GitHub issue sync completed for all tasks T001-T087 as issues #550-#636 in
  `yshishenya/crisp`.
- After implementation validation, all GitHub issues #550-#636 were closed with
  evidence comments.
- Earlier Linear sync created issues for T001-T079: YSH-274 through YSH-352.
- T080-T087 were not created in Linear because the workspace returned
  `USAGE_LIMIT_EXCEEDED` for `activeIssueCount`.

## Closure Impact

This is not a remaining blocker for `015`.

Do not run `.specify/extensions/linear-sync/scripts/linear_sync.py` for feature
closure unless the user explicitly re-enables Linear for this repository or for
this feature.
