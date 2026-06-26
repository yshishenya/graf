# Validation Log: Desktop UI Polish

## Baseline

- branch: `codex/054-desktop-ui-polish`
- feature: `specs/054-desktop-ui-polish`
- clean-room reference: user supplied KRISP appshot and current 2brain Rec appshot; used for density and layout rhythm only.
- implementation scope: existing server cabinet HTML/CSS and existing SwiftUI shell constants.

## 2026-06-26 Validation

- prerequisites: `SPECIFY_FEATURE_DIRECTORY=specs/054-desktop-ui-polish .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` passed; `FEATURE_DIR` resolved to `specs/054-desktop-ui-polish`.
- targeted red pass before implementation: server assertions for `1120px` workspace and `46px` rows failed before CSS changes.
- targeted server pass: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py::test_list_shell_renders_dense_controls_without_marketing_copy tests/integration/test_cabinet_meeting_list.py::test_desktop_embedded_list_keeps_review_workspace_but_hides_native_creation_controls` passed, 2 tests.
- targeted macOS pass: `swift test --package-path apps/macos --disable-swift-testing --filter AppControlAccessibilityTests/testDesktopCabinetLayoutStartsWithNativeCaptureThenMeetings` passed, 1 test.
- focused server pass: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_list.py` passed, 17 tests, 1 pytest-asyncio deprecation warning.
- focused macOS pass: `swift test --package-path apps/macos --disable-swift-testing --filter 'AppControlAccessibilityTests|DesktopCabinetWorkspaceTests'` passed, 34 tests.
- optional browser proof: initial run without bundled `NODE_PATH` could not find `playwright`; rerun with bundled Codex Node packages passed with 4 viewports and `failures: []`.
- forbidden-content scan: matches were limited to policy text and the scan command itself in 054 docs; no live private values were found.
- GitHub issue sync: created and closed feature 054 issues #1869 through #1881 for T001 through T013, each with Russian closure evidence. `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py` passed.
- right rail follow-up: compact inspector was reduced to expand, recording status, queue badge, and refresh only; decorative `Off`, video, mic/speaker, and pseudo-toggle labels were removed. `swift test --package-path apps/macos --disable-swift-testing --filter AppControlAccessibilityTests/testDesktopCabinetLayoutStartsWithNativeCaptureThenMeetings` passed.
- right rail toggle follow-up: expand/collapse button is now anchored with the same `top=10` and `trailing=4` inset in compact and expanded inspector states, so the button does not jump after toggling. `swift test --package-path apps/macos --disable-swift-testing --filter 'AppControlAccessibilityTests|DesktopCabinetWorkspaceTests'` passed, 34 tests.
- closeout CI: first `infra/scripts/ci-local.sh` run failed on `test_current_status_records_052_live_ui_proof_and_deployed_dispatch_boundary` because `docs/current-product-status.md` no longer included the historical `missing auth context` phrase required by the 052 status contract. The doc was updated, the targeted status test passed, and the rerun of `infra/scripts/ci-local.sh` passed with `627 passed, 4 skipped`, server lint OK, Python compile OK, production compose config rendered, deployment evidence scan pass, and `ci_local_result=pass`.
