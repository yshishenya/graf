# Final Closeout: Ponytail Refactor Audit

**Date**: 2026-06-30
**Branch**: `codex/071-ponytail-refactor`
**Release branch**: `codex/071-ponytail-refactor-release`
**Risk / validation lane**: significant/high-risk cleanup.
**Deploy status**: no deploy or production smoke in the implementation closeout; release/deploy is handled as a separate release lane.

## Completed Cleanup

### Batch A: Server cleanup

Removed:

- `structlog` from `apps/server/pyproject.toml`, `apps/server/constraints.txt`, and `apps/server/uv.lock`.
- unused private/internal server parameters and call arguments in admin membership decisions, auth route handlers, cabinet rendering helpers, deletion lifecycle lookup, cabinet egress policy helper, and ingest lifecycle blocking helper.
- small redundant local expressions and test stub noise.

Validation:

- `rg -n "structlog" apps/server apps/macos infra scripts .specify AGENTS.md`: pass, no active matches.
- server Ruff: pass.
- Vulture at 80 and 70 confidence: pass, no findings.
- JS syntax and shell syntax checks: pass.
- focused Batch A pytest: `63 passed in 3.08s`.
- `infra/scripts/ci-local.sh`: `987 passed, 4 skipped`, `deployment_evidence_scan=pass`, `ci_local_result=pass`.
- `cd apps/macos && swift test`: `706 tests, 0 failures`.
- `git diff --check`: pass.

### Batch B: Python dev dependency cleanup

Removed:

- `httpx2` from server dev dependencies.
- lockfile-only transitive packages `httpcore2` and `truststore`.

Validation:

- `rg -n "httpx2|httpcore2|truststore" ...`: pass for active source/dependency surfaces after removal.
- `cd apps/server && uv lock --check`: pass, `Resolved 53 packages`.
- `cd apps/server && uv tree --all-groups --depth 1`: pass, dependency tree no longer includes `httpx2`, `httpcore2`, or `truststore`.
- server Ruff: pass.
- focused HTTP/auth/provider tests: `38 passed in 2.82s`.
- `infra/scripts/ci-local.sh`: `987 passed, 4 skipped`, `deployment_evidence_scan=pass`, `ci_local_result=pass`.
- `git diff --check`: pass.

## Retained Candidates

Not removed:

- provider adapter callback arguments (`credentials`, `http_client`, `now`) because they are part of the shared auth-provider contract;
- `pytest-asyncio`, `python-multipart`, `asyncpg`, and `uvicorn[standard]` because they are plugin/parser/driver/runtime entrypoints;
- large cabinet presentation files because they need a dedicated presentation split, not opportunistic deletion;
- `htmx-2.0.10.min.js` because it is a vendored browser runtime asset;
- macOS capture/upload/diagnostic large files because they protect capture truth, upload custody, metadata-only diagnostics, and deletion/purge semantics;
- AudioDriver proof code because it is parked future-routing evidence;
- deployment/smoke/backup/restore scripts because they are operational safety entrypoints.

## macOS Cleanup Decision

No macOS cleanup batch was applied. `candidates-macos.md` did not prove a safe deletion candidate. The existing full Swift validation remains green, but there is no macOS source diff in this slice.

## Worktree Separation

071-owned changes:

- `specs/071-ponytail-refactor/`
- `AGENTS.md` SPECKIT pointer update
- server cleanup under `apps/server/`
- `CHANGELOG.md` Unreleased entries

Kept separate:

- pre-existing/generated `.specify/*` template/config changes
- generated `.agents/skills/speckit-*` files

## Final Notes

- No new runtime dependency, framework, abstraction, product behavior, auth boundary, capture behavior, deletion semantics, storage schema, deployment behavior, or production release was introduced.
- The release branch was transplanted onto `origin/master` at `b8272099` and intentionally excludes generated `.specify/*` and `.agents/*` workspace noise.
- Rebase conflict resolution kept the 071 removal of the unused `_page_shell(active=...)` parameter while preserving the current `cabinet/pages/shell.html` template contract.
- Release-branch validation: `SPECIFY_FEATURE_DIRECTORY=specs/071-ponytail-refactor .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` passed; `uv lock --check` passed with 53 packages; server Ruff passed; Vulture at 80 confidence passed; focused server regression tests passed with `104 passed, 1 warning`; `infra/scripts/ci-local.sh` passed with `989 passed, 4 skipped`, `deployment_evidence_scan=pass`, and `ci_local_result=pass`; `cd apps/macos && swift test` passed with `708 tests, 0 failures`; diff checks passed.
