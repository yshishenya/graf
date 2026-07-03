# Quickstart: Dead Code Batch 5

Run from repository root.

## Compile Probe

```sh
swift build --package-path apps/macos
```

Expected: build succeeds after removing the selected `Foundation` import lines.

## Focused Validation

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'LatencyGateTests|LowResourceRouteTruthTests|LowResourceRouteLifecycleTests|DesktopUploadQueueTests|RecordingPrerequisiteGateTests'
```

Expected: touched buffering, latency, prerequisite, and low-resource route-truth
surfaces pass.

## Closeout

```sh
git diff --check
SPECIFY_FEATURE_DIRECTORY=specs/078-dead-code-batch-5 .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
infra/scripts/ci-local.sh
```

Expected: prerequisites and issue canon pass, and `ci_local_result=pass`.
