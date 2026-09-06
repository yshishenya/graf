# Contract: Packaged macOS startup

## Resource resolution

1. A packaged `GRAF.app` resolves the target registry only from its standard
   resource root:
   `Contents/Resources/TwoBrainRecMacOS_TwoBrainRecAppCore.bundle/Resources/meeting-target-registry-baseline.json`.
2. SwiftPM development/test execution may resolve the same JSON through the
   generated module bundle.
3. Missing packaged bundle, missing JSON or an unreadable candidate returns
   no bundled URL; it must not invoke `Bundle.module` or terminate the process.
4. Registry content validation and cache/remote resolution remain owned by the
   existing `MeetingTargetRegistryStore`.

## Release smoke CLI

```text
validate-packaged-app-launch.sh /absolute/path/GRAF.app [minimum-seconds] [native|arm64|x86_64]
```

- Requires an absolute `.app` directory with `Contents/Info.plist` and an
  executable `Contents/MacOS/GRAF`.
- Launches that exact binary and records its direct child PID.
- Uses an isolated temporary HOME and closed loopback product origins.
- Runs the explicitly requested universal slice when an architecture is given.
- Passes only if that PID remains alive for at least five seconds.
- On exit or interruption, terminates and waits only for its own child.
- Fails for malformed bundles, missing binaries and early process exit.
- Emits bounded metadata only; never process logs or private local paths in
  committed/public evidence.

## Publication ordering

The signing workflow must pass packaged startup before appcast generation or
upload. Final checksums are derived after app and PKG stapling and final ZIP
creation. The public appcast is the last mutable production file.
