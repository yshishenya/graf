# Feature 099 Current-Master Integration Receipt

**Feature**: `099-review-m4a-normalization`
**Date**: 2026-07-14
**Integration base**: `98d57f7431d302b0d2060fb020fc2b320f854753`

## Base update

The validated but uncommitted feature working copy was preserved in stash
`0288554b89f7af7b00f4dab9eade284ac581ed14`, the feature branch was
fast-forwarded from `ab818459467d11006e24575242236b5f7872d8e4` to current
`origin/master`, and the working copy was reapplied. The new base contains 27
master commits, including the separate `v2026.07.14.7` interface release.

Twelve paths had changes on both sides. Git merged eight automatically. Four
explicit conflicts were resolved by preserving both current-master behavior
and feature-099 behavior:

- `AGENTS.md` points at the active 099 plan in this feature worktree;
- meeting-row rendering retains the current inactive-upload presentation and
  adds the independent playback state token;
- cabinet JavaScript retains current delete-focus recovery and adds automatic
  playback recovery state;
- shell tests retain the compact current meeting-list contract and current
  fetch-based deletion contract while asserting the new playback projection
  and poll request.

After resolution, `git diff --check` passed, unmerged paths were zero, and the
index was returned to an unstaged state. `HEAD` and `origin/master` both
resolved to the integration base above.

## Post-integration validation

The directly affected cabinet surface passed:

```text
164 passed, 1 pre-existing Starlette/httpx warning, 57.16s
```

The canonical repository gate then passed from the integrated working copy:

```text
infra/scripts/ci-local.sh
ci_local_result=pass
```

- macOS build and contract validation: pass;
- macOS Swift tests: `643/643`;
- server: `1713 passed`, `21 skipped`, `409.11s`;
- Ruff, Python compile, production Compose rendering and deployment evidence
  scan: pass.

The canonical script intentionally leaves its destructive PostgreSQL probe
blocked when no disposable URL is supplied. A fresh native disposable
PostgreSQL cluster therefore ran the real integration subset and direct probe:

```text
23 passed, 1 pre-existing warning, 1.68s
rls_validation_result=pass
destructive_probe_database=disposable
ready_for_production_truth=true
probe_suite=direct_sql_rls_probes
postgres_099_native_residue=0
```

An initial disposable cluster used the production-shaped database name and
was correctly rejected by the live-database guard before the direct probe.
It was deleted, then the successful run used an explicitly test-only database
name and test-only credential. No production database was inspected or
changed.

## Current-master Chrome regression

The same synthetic local harness was rerun in real Chrome against the merged
`v2026.07.14.7` cabinet surface:

- all four list records projected preparing, available, unavailable and
  transcript-independent playback truth;
- `1440x900` and `740x900` both had `scrollWidth == clientWidth` with four
  visible records;
- narrow keyboard order reached the focus-visible `К содержимому` link and
  then the focus-visible `Поиск встреч` input, both with a solid 2 px outline;
- reduced-motion emulation produced `1e-06s` animation and transition
  durations and `scroll-behavior: auto`;
- preparing detail had no audio element, range input or repair/retry control;
- automatic polling projected the real player after publication without a
  repair action; the audio element reached `readyState=4`, duration `40s`;
- Play advanced to `1.935s`; Pause held `10.532s` across `1.2s`; forward seek
  moved `10.532s -> 25.532s` while paused;
- Chrome received `206`, `Range: bytes=0-` and
  `Content-Range: bytes 0-35620/35621`;
- corrupt detail showed the safe terminal copy with no audio, range or
  repair/retry control;
- Chrome warning/error log was empty.

Viewport and media emulation were reset. The agent-created Chrome tab, local
proxy and harness were stopped; ports `8099` and `8100`, the state file and
temporary harness directories had zero residue.

## Independent-review fixes and final rerun

The current-master candidate received three independent reviews. Their
actionable findings were resolved before approval:

- a central SQLAlchemy `after_begin` hook now replays transaction-local tenant
  context after every internal PostgreSQL commit; the three exact restricted
  media-role regressions passed, and the complete PostgreSQL normalization file
  passed `12/12`;
- temporary poll failures now show a visible live recovery notice while
  continuing automatically; valid responses clear it;
- the status document now says `local production-equivalent` and does not
  claim that feature 099 is already deployed;
- real Chrome deletion during an active poll produced the terminal unavailable
  fragment, `0` player controls, no resurrection after delayed publication and
  `404` on the deleted detail.

The full canonical CI was rerun after the last code-affecting fix and returned
`ci_local_result=pass`: macOS `643/643`, server `1713 passed, 21 skipped`, Ruff,
compile, Compose rendering, deployment evidence scan and diff check all passed.
The three additional skips are the new environment-gated PostgreSQL
commit-boundary tests, which passed in the disposable native PostgreSQL run.

## Boundary

This receipt validates the local integration candidate only. No file is
staged or committed, no PR exists, and no release or production mutation was
performed. Feature 097 and its deferred standalone security scan were not
opened, resumed, failed or completed.
