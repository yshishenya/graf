# Validation Log: Cabinet Runtime Truth

This file records metadata-only validation for feature `047`.

## 2026-06-24

- Started feature branch `047-cabinet-runtime-truth` from canonical `master` at
  `895de8b` after release `v2026.06.24.2`.
- User-reported problem: after server restart, the macOS app looked like the
  cabinet/server was OK, then later showed auth/login trouble while the server
  was unavailable.
- Initial diagnosis: active old worktree `e040` was still on
  `045-transcription-results-pipeline` and did not include the cabinet-runtime
  fix. New work proceeds on 047 from fresh master to avoid mutating old dirty
  045 artifacts.
- Spec Kit prerequisites for `047` passed with available docs:
  `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`.
- Checklist status: `requirements.md` 16/16 complete, `ux.md` 11/11 complete.
- Read-only analyze pass found no blocking placeholders or clarification
  markers, no constitution-gate gap in `plan.md`, and task coverage for all
  `FR-001` through `FR-010` plus `SC-001` through `SC-007`.
- Focused macOS cabinet validation passed:
  - `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`
    result: `20 tests, 0 failures`.
  - `swift test --package-path apps/macos --filter DesktopCabinetConfigurationTests`
    result: `15 tests, 0 failures`.
  - `swift test --package-path apps/macos --filter AppControlAccessibilityTests`
    result: `9 tests, 0 failures`.
- Covered regression truth: configured/loading cabinet is neutral and not a
  green success state; offline/timeout show server unavailable; login/sign-up
  finished routes map to `expiredSession`; active recording shell invariant
  stays true for every cabinet state.

## 2026-06-25

- Synced `047-cabinet-runtime-truth` on top of `origin/master` at
  `94e6cbfa2c15d9e3e94ee8d533c13d91b0f5c4d9`, after deployed feature `048`.
  The old dirty `045` worktree was not used for implementation.
- Spec Kit prerequisites passed for `specs/047-cabinet-runtime-truth` with
  `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and
  `tasks.md` available. Checklist status remained complete:
  `requirements.md` 16/16 and `ux.md` 11/11.
- Focused macOS cabinet validation passed again after the `048` sync:
  - `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`
    result: `20 tests, 0 failures`.
  - `swift test --package-path apps/macos --filter DesktopCabinetConfigurationTests`
    result: `15 tests, 0 failures`.
  - `swift test --package-path apps/macos --filter AppControlAccessibilityTests`
    result: `9 tests, 0 failures`.
- Focused server cabinet validation passed after the `048` sync:
  `PYTHONPATH=src uv run --extra dev pytest -q ...cabinet...` result:
  `43 passed`.
- Fixture-backed Playwright/Chrome browser runtime validation passed using
  synthetic review content: web ready desktop, web ready mobile, embedded ready
  desktop, embedded ready mobile, unavailable desktop, and unavailable mobile
  all reported `failures=[]`, `horizontalOverflow=0`, and matching playback
  availability/unavailability truth. A first direct Node invocation failed
  because this checkout had no local `playwright` module; the same script
  passed with the Codex Desktop bundled Node dependency path.
- Real temporary FastAPI/SQLite/FakeMinIO runtime validation passed using
  synthetic data: browser checks opened ordinary web, mobile web, and desktop
  embedded routes with `failures=[]`; playback range response returned `206`
  with safe range headers; no visible audio download link was present.
- Production health truth check reported live `{"status":"ok"}` and ready
  `{"status":"ready"}`. This proves only current server health, not desktop
  shell readiness by itself.
- Full macOS package gate passed:
  `swift test --package-path apps/macos` result `579 tests, 0 failures`.
- Full local CI passed:
  `infra/scripts/ci-local.sh` result `ci_local_result=pass`, server tests
  `570 passed, 4 skipped, 8 warnings`, server lint passed, Python compile
  passed, deployment evidence scan passed.
- Deploy dry-run passed:
  `infra/scripts/cd-remote.sh --dry-run` result `deploy_result=dry_run`,
  remote host `2brain.dev`, remote path `/opt/projects/2brain-rec`, branch
  `047-cabinet-runtime-truth`.
- GitHub issue sync completed for all `047` tasks: issues `#1611` through
  `#1634` were created, `specs/047-cabinet-runtime-truth/issues.md` was
  recorded, and issue canon validation passed with
  `github-issue-canon: OK (24 Spec Kit issue(s) checked)`.
- Product status was updated to record 047 as locally implemented and
  validated on top of deployed 048, while preserving the truth that 047 is not
  merged, released, or deployed yet.
