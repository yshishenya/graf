# Swift Package Evidence

**Date**: 2026-06-30
**Scope**: `apps/macos/Package.swift`, macOS Swift/C/C++ source, macOS validation scripts, and package tests.

## Package Shape

`apps/macos/Package.swift` declares no remote package dependencies. All products and targets are local:

- libraries: `TwoBrainRecShared`, `TwoBrainRecAppCore`
- executables: `TwoBrainRecApp`, `ContractValidation`, `LeakageValidation`, `MeetingMuteTruthRuntimeProof`, `WebRTCAEC3Validation`
- targets: `CShmHelpers`, `TwoBrainRecShared`, `TwoBrainRecAppCore`, executable targets above, and `TwoBrainRecSharedTests`

## Evidence

- `CShmHelpers` is a local C target used by `TwoBrainRecShared`.
- `TwoBrainRecShared` and `TwoBrainRecAppCore` are shared by the app, package tests, and validation executables.
- Validation executables are exposed as products and are referenced by macOS scripts and release evidence workflows.
- `swift test` completed successfully with `706 tests, 0 failures`.

## Decision

No Swift package dependency can be removed from `Package.swift` in this phase because there are no external dependencies to prune. Target/file cleanup must come from source-level candidate analysis, not dependency metadata.

## Exclusions

- `apps/macos/.build/` is generated build output and is excluded from code inventory.
- Image assets, fixtures, and app resources are not dependency bloat unless a later task proves a duplicate or obsolete source-of-truth replacement.
