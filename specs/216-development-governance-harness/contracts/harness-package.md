# Contract: Reusable Harness Package

## Portable core

The package may contain generic rules, templates, shell/Python validators,
context preflight, claim/fragment/CI schemas, self-tests and adapter interfaces.

## Project adapter

Each consumer supplies repository root, integration branch, build commands,
Dev manifest adapter, app identity checks, product gates and release commands.
Adapters are configuration and code owned by the consumer; they are not copied
from GRAF automatically.

## Publication gate

Before publishing an immutable SemVer, run self-test, shellcheck/lint where
available, secret scan, absolute-path scan, provenance/license check and a clean
sample-project installation. A failed gate blocks tag and release.

## Compatibility

Every harness release has migration notes, supported tool versions, a pinned
checksum/ref and a previous version that can be restored.
