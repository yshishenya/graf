# Quickstart: Dead Code Batch 2

Run from repository root.

## Evidence

```sh
rg -n "statusChip\\(" apps/macos apps/server/src apps/server/tests infra scripts
rg -n "waitUntil\\(" apps/macos apps/server/src apps/server/tests infra scripts
```

After deletion both commands should return no matches.

## Focused Validation

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'LivePassthroughPolicyTests|DesktopMeetingShellWebViewBoundaryTests|CaptureControlTests'
```

Run full Swift validation before closeout:

```sh
swift test --package-path apps/macos --disable-swift-testing
```

## Closeout

```sh
git diff --check
infra/scripts/ci-local.sh
```
