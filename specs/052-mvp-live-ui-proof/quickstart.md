# Quickstart: MVP Live Owner Journey And UI Proof

Run commands from the repository root.

## 1. Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/052-mvp-live-ui-proof \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: JSON points to `specs/052-mvp-live-ui-proof`.

## 2. Focused Server Readiness, Outcomes, And Cabinet Tests

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_mvp_launch_proof_contract.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_launch_proof_readiness.py \
  tests/integration/test_mvp_launch_status_truth.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_outcomes.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_cabinet_meeting_detail.py
```

Expected: all tests pass after 052 updates.

## 3. Production Owner Journey Probe

```sh
python3 specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py
```

Expected: metadata-only output classifies each P1 owner journey gate as
`pass`, `fail`, `blocked`, or `unproven`. No raw content or secrets are printed
or committed.

## 4. Browser Runtime UI Proof

```sh
NODE_PATH="${CODEX_NODE_MODULES:-node_modules}" \
  "${CODEX_NODE_BIN:-node}" \
  specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs
```

Expected: web desktop, web compact, and embedded review checks report
`failures=[]`, no horizontal overflow, no blocking console errors, visible
speaker lanes, visible outcome states, and working timestamp seek.

## 5. macOS Tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopCabinet|CaptureControl|DesktopUploadQueue|EmbeddedCabinet'
```

Expected: focused macOS tests pass.

Run the full macOS suite when native code changes:

```sh
swift test --package-path apps/macos --disable-swift-testing
```

## 6. Installed App Check

```sh
defaults read "/Applications/2brain Rec.app/Contents/Info" CFBundleShortVersionString
codesign --verify --deep --strict "/Applications/2brain Rec.app"
pgrep -fl "2brain Rec|TwoBrainRecApp" || true
```

Expected: installed app version matches the release under validation, signing
verification passes for the local build, and process state is recorded without
interrupting an active recording.

## 7. KRISP Reference And 2brain UI Review

Inspect KRISP web/app reference and 2brain web/desktop review surfaces without
committing private screenshots or content. Record only clean-room interaction
findings in:

```text
specs/052-mvp-live-ui-proof/evidence/ui-reference-review.md
```

Expected: speaker timeline, playback, timestamp seek, transcript, outcomes,
auth/unavailable states, and brand-distance notes are classified without
private content.

## 8. Production Health And Deployment Truth

```sh
curl -fsS https://rec.2brain.pro/api/v1/health/live
curl -fsS https://rec.2brain.pro/api/v1/health/ready
ssh 2brain.dev 'cd /opt/projects/2brain-rec && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD'
```

Expected: live/ready are healthy and remote SHA matches the intended release.

## 9. Full Local Gate

```sh
infra/scripts/ci-local.sh
```

Expected: `ci_local_result=pass`.

## 10. Deploy Gate

```sh
infra/scripts/cd-remote.sh --dry-run
```

Expected: `deploy_result=dry_run`.

Run execute only after PR/release gate is ready:

```sh
infra/scripts/cd-remote.sh --execute
```

Expected: `deploy_result=pass` and production smoke returns a bounded
readiness verdict.

## 11. Forbidden Content Scan

```sh
rg -n -i \
  'transcript text|signed url|secret|token|password|cookie|set-cookie|authorization:|object key|/(Users|home)/[^ ]+|private meeting|private outcome' \
  specs/052-mvp-live-ui-proof docs/evidence/052-mvp-live-ui-proof docs/current-product-status.md CHANGELOG.md
```

Expected: no forbidden private content in committed evidence. Literal policy
phrases in contracts/specs are allowed only when they describe forbidden
classes, not live values.
