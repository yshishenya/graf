# Plan: Universal macOS installer

Risk lane: significant packaging/compatibility slice; full Spec Kit artifacts
and focused installer, Swift, public download, and local CI validation are
required. Production publication remains Developer ID/notarization gated.

1. Build the macOS app twice with SwiftPM (`arm64` and `x86_64`) in isolated
   scratch paths, combine the executables with `lipo`, and verify final slices.
2. Keep the existing app-only package contract and rename the public artifact to
   `graf.pkg`.
3. Accept Intel in `PlatformSupport` while retaining macOS 14.5 floor and reject
   unknown architectures.
4. Update public download template, asset, tests, PRD, current status, README,
   changelog, and release evidence to state one universal installer.
5. Run focused checks, local CI, PR review, merge, and CalVer release closeout.
