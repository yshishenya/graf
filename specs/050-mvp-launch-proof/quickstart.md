# Quickstart: MVP Launch Proof

Run commands from the repository root.

## 1. Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/050-mvp-launch-proof \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: JSON points to `specs/050-mvp-launch-proof`.

## 2. Focused Server Readiness And Cabinet Tests

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_mvp_loop_readiness_matrix.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_outcomes.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_cabinet_meeting_detail.py
```

Expected: all tests pass.

## 3. Browser Runtime UI Proof

```sh
NODE_PATH="${CODEX_NODE_MODULES:-node_modules}" \
  "${CODEX_NODE_BIN:-node}" \
  specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs
```

Expected: desktop, embedded, and mobile-width review checks report
`failures=[]`, no horizontal overflow, no console errors, and working timestamp
seek.

## 4. macOS Tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopCabinet|CaptureControl|DesktopUploadQueue|EmbeddedCabinet'
```

Expected: focused macOS tests pass.

Run the full macOS suite when native code changes:

```sh
swift test --package-path apps/macos --disable-swift-testing
```

## 5. Production Health And Deployment Truth

```sh
curl -fsS https://rec.2brain.pro/api/v1/health/live
curl -fsS https://rec.2brain.pro/api/v1/health/ready
ssh 2brain.dev 'cd /opt/projects/2brain-rec && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD'
```

Expected: live/ready are healthy and remote SHA matches the intended release.

## 6. Full Local Gate

```sh
infra/scripts/ci-local.sh
```

Expected: `ci_local_result=pass`.

## 7. Deploy Gate

```sh
infra/scripts/cd-remote.sh --dry-run
```

Expected: `deploy_result=dry_run`.

Run execute only after PR/release gate is ready:

```sh
infra/scripts/cd-remote.sh --execute
```

Expected: `deploy_result=pass` and production smoke returns
`readiness_verdict=infra_smoke_ready`.

## 8. Forbidden Content Scan

```sh
rg -n -i \
  'transcript text|signed url|secret|token|password|cookie|set-cookie|authorization:|object key|/(Users|home)/[^ ]+|private meeting' \
  specs/050-mvp-launch-proof docs/evidence/050-mvp-launch-proof docs/current-product-status.md CHANGELOG.md
```

Expected: no forbidden private content in committed evidence. Literal policy
phrases in contracts/specs are allowed only when they describe forbidden
classes, not live values.
