# Quickstart: Dead Code Batch 3

Run from repository root.

## Compile Probe

```sh
swift build --package-path apps/macos
```

Expected: build succeeds after removing the three import lines.

## Focused Validation

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'CaptureControlTests|BluetoothRoutePolicyTests|VolumeMuteMappingTests'
```

Expected: touched capture, Bluetooth policy, and volume/mute surfaces pass.

## Closeout

```sh
git diff --check
infra/scripts/ci-local.sh
```

Expected: `ci_local_result=pass`.
