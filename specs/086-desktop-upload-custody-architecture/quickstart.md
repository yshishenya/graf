# Quickstart: Desktop Upload Custody Architecture

This quickstart validates the 086 read-only architecture package.

## Preconditions

- Work from a clean worktree based on fresh `origin/master`.
- Do not change product/runtime code, dependency declarations, migrations,
  release files, generated artifacts, or production state.
- Do not run production deploy.

## Stage-One Validation Commands

```sh
SPECIFY_FEATURE_DIRECTORY=/private/tmp/crisp-086-desktop-upload-custody-architecture/specs/086-desktop-upload-custody-architecture \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks

placeholder_pattern='[T]ODO|[T]KTK|\\?\\?\\?|<place''holder>|[I]NSERT|[T]BD|NEEDS[[:space:]]+CLARIFICATION'
rg -n "$placeholder_pattern" specs/086-desktop-upload-custody-architecture

git diff --check
```

Expected result:

- Spec Kit prerequisite command returns the 086 feature directory and available
  docs.
- Placeholder scan returns no unresolved template placeholders.
- `git diff --check` returns no whitespace errors.

## Evidence Refresh Commands

These commands are safe read-only inputs for future roadmap refreshes:

```sh
git ls-files 'apps/macos/RecApp/Sources/Upload/*.swift' \
  'apps/macos/Shared/Tests/*Upload*' \
  'apps/macos/Shared/Tests/*Purge*' \
  'apps/server/src/twobrain_rec_server/api/*.py' \
  'apps/server/src/twobrain_rec_server/ingest/*.py' \
  'apps/server/src/twobrain_rec_server/deletion/*.py' \
  'apps/server/src/twobrain_rec_server/support/*.py'

rg -n "DesktopUploadQueueService|DesktopUploadClient|DesktopUploadCustodyProjection|DesktopLocalPurgeTask|SupportIncident" \
  apps/macos apps/server/src/twobrain_rec_server apps/server/tests
```

## Future Implementation Gates

Run these before merging future 086-derived code PRs when their boundary is
touched:

```sh
swift test --package-path apps/macos
infra/scripts/ci-local.sh
```

Focused gates by boundary:

- Queue/custody PRs: desktop upload queue, custody projection, and persistence
  compatibility tests.
- Upload transport PRs: upload client tests and server ingest contract tests.
- Local purge PRs: desktop local purge tests plus server deletion/local purge
  tests.
- Support incident PRs: support payload/redaction tests and no-secret evidence
  scan.

## Out Of Scope

- Production deploy.
- Runtime behavior changes.
- Schema/API changes.
- Dependency changes.
- Deleting code.
