# Feature 098 Pre-Implementation Baseline

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Spec task evidence**: T001, T004
**GitHub Issues**: #3082, #3085

## Verified Anchor

- Worktree: `/Users/yshishenya/.codex/worktrees/098-calendar-auto-context-match`
- Branch: `codex/098-calendar-auto-context-match`
- Pre-implementation `HEAD`: `d912a21c68c5ff0823bb89abd4d045bb873723cf`
- Validated base `origin/master`: `d912a21c68c5ff0823bb89abd4d045bb873723cf`
- Remote: `git@github.com:yshishenya/crisp.git`
- Feature directory: `specs/098-calendar-auto-context-match`
- `.specify/feature.json`: `{"feature_directory":"specs/098-calendar-auto-context-match","spec_path":"specs/098-calendar-auto-context-match"}`

The physical worktree name is not treated as authority; branch, feature
directory, feature metadata and exact Git SHA agree.

## Dirty-Tree Accounting

Before implementation code began, this worktree contained only the expected
098 planning artifacts:

- modified `specs/098-calendar-auto-context-match/spec.md`;
- untracked 098 `plan.md`, `research.md`, `data-model.md`, `quickstart.md`,
  `tasks.md`, `contracts/` and `checklists/calendar-context-readiness.md`.

No source, test, migration, release or runtime file was dirty at this anchor.
The unrelated detached worktree at
`/Users/yshishenya/.codex/worktrees/30ac/crisp` remains outside this feature
worktree and must not be reset, cleaned, staged or included in 098 commits.
The canonical checkout `/Users/yshishenya/Documents/crisp` is also preserved;
implementation is isolated here.

## Spec Kit And Tracker Baseline

Commands and results:

```text
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
PASS: FEATURE_DIR=/Users/yshishenya/.codex/worktrees/098-calendar-auto-context-match/specs/098-calendar-auto-context-match

checklist scan
PASS: requirements.md 16/16
PASS: calendar-context-readiness.md 47/47

$speckit-analyze
PASS: 52 FR + 17 SC, 109 tasks, 100% inferred requirement coverage,
      0 Critical/High/Medium/Low findings

$speckit-taskstoissues + mandatory canon validation
PASS: 109/109 task-backed Issues (#3082-#3190), no missing/extra/duplicate IDs
PASS: github-issue-canon: OK (211 Spec Kit issue(s) checked)
```

The optional pre-implementation git hook was deliberately not run. Feature
098 implementation is not committed until the final validated diff receives
the required integration approval.

## Focused Runtime Baseline

Command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_recording_context.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/integration/test_calendar_access_policy.py \
  tests/integration/test_calendar_provider_failures.py
```

Result:

```text
50 passed, 1 StarletteDeprecationWarning in 4.69s
```

Classification: existing calendar context, privacy projection, access policy
and provider-failure baseline is green. The warning is dependency deprecation
noise, not a product assertion, crash or fixture failure.

## Project Setup Verification

- Git repository detection passed.
- The existing `.gitignore` covers universal files, secrets/environment
  overrides, Python caches/builds, Swift/Xcode outputs and editor metadata.
- The existing `.dockerignore` covers git data, secrets, Python/Swift/Node
  caches and build output used by the repository Dockerfile.
- No ESLint, Prettier, npm publishing, Terraform or Helm surface is detected,
  so no additional ignore file is required.
- No ignore file was changed.

## Feature Boundary

Included:

- live, non-blocking recording-start calendar resolve against stored snapshots;
- exact 24-hour attempt TTL and atomic same-owner/workspace/device consumption;
- deterministic clear/no-match/ambiguous/private/stale outcomes;
- immutable safe title, roster and recurring context;
- explicit start-time decline distinct from later context clear;
- server-owned cabinet UI shared by browser and embedded macOS;
- ordinary authorization, privacy, lifecycle and forbidden-content acceptance
  tests using synthetic metadata only.

Excluded:

- feature 097 and the separately deferred standalone Codex Security scan;
- retrospective matching, manual-upload matching and offline recovery matching;
- calendar/provider writes, auto-record, attendee-based access/share/delivery;
- speaker identity/name assignment and a second native review UI;
- any live calendar, private meeting, transcript or audio fixture data.

## First Implementation Checkpoint

Phase 1 may add only bounded synthetic server/macOS fixtures and this evidence.
Phase 2 must then add failing migration/RLS/contract coverage before the
foundation models and migration are implemented. No user-story production
path starts until the Phase 2 schema, title provenance, RLS inventory and
shared contract checkpoint passes.

## Phase 1 Fixture Receipts

T002 server fixtures:

```text
PYTHONPATH=src uv run --extra dev ruff check \
  tests/fixtures/calendar_auto_match.py \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/contract/test_calendar_rls_contract.py \
  tests/integration/test_rls_postgres_migrations.py
PASS: All checks passed

PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_provider_fixtures.py
PASS: 6 passed, 1 existing StarletteDeprecationWarning in 0.01s
```

The new deterministic fixture module builds clear, overlap,
private/free-busy, stale/latest-failed and recurring scenarios. Test-only caps
are 4 sources, 50 events, 10 visible candidates and 100 roster items. Fixture
identities require `.test`; descriptions, attachments, raw links and passcodes
are rejected.

T003 macOS fixtures:

```text
swift test --package-path apps/macos --disable-swift-testing \
  --filter CalendarSettingsFixturesTests
PASS: build complete; 3 tests, 0 failures in 0.007s
```

The Swift builders cover automatic, explicit selection, explicit start-time
decline, ambiguous resolve, transport failure and recovered queue defaults.
The contract-shaped fixture proves ISO-8601 encoding and an exact 24-hour TTL.
No build, setup, assertion or fixture failure occurred.
