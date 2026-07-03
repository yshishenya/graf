# Quickstart: Dead Code Batch 4

Run from repository root.

## Compile Probe

```sh
swift build --package-path apps/macos
```

Expected: build succeeds after removing the selected `Foundation` import lines.

## Focused Validation

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'BluetoothRoutePolicyTests|GuidedDeviceManagementTests|RecordingPrerequisiteGateTests|RecordingRouteMetadataTests|LiveRouteClientActivityTests|RecordingTimelineEvidenceTests|SystemAudioAccessibilityTests|SystemAudioResponsiveStateTests'
```

Expected: touched route, device-management, prerequisite, metadata, timeline,
and shared model surfaces pass.

## Closeout

```sh
git diff --check
SPECIFY_FEATURE_DIRECTORY=specs/077-dead-code-batch-4 .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
infra/scripts/ci-local.sh
```

Expected: prerequisites and issue canon pass, and `ci_local_result=pass`.
