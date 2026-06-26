# Quickstart: Desktop UI Polish

Run from the repository root.

## 1. Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/054-desktop-ui-polish \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: JSON points to `specs/054-desktop-ui-polish`.

## 2. Focused Server UI Tests

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py
```

Expected: web list/detail shell tests pass.

## 3. Focused macOS Shell Tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'AppControlAccessibilityTests|DesktopCabinetWorkspaceTests'
```

Expected: native shell layout constants and cabinet route tests pass.

## 4. Optional Browser Runtime Check

```sh
NODE_PATH="${CODEX_NODE_MODULES:-node_modules}" \
  "${CODEX_NODE_BIN:-node}" \
  specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs
```

Expected: no blocking layout regressions in existing browser proof.

## 5. Forbidden Content Scan

```sh
rg -n -i \
  'signed url|secret|token|password|cookie|set-cookie|authorization:|object key|/(Users|home)/[^ ]+|private meeting|private outcome' \
  specs/054-desktop-ui-polish
```

Expected: no live private values.
