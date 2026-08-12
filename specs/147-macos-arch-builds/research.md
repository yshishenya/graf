# Research: Universal macOS Installer

## Decision 1: Ship one universal installer

Apple's current macOS guidance treats a universal binary containing `arm64`
and `x86_64` as the native distribution model for one app. macOS selects the
native slice on each machine. This matches the requested UX: one download and
no architecture decision on the public page.

Source: [Building a universal macOS binary](https://developer.apple.com/documentation/apple-silicon/building-a-universal-macos-binary)

## Decision 2: Merge the existing SwiftPM outputs at packaging time

The current package is SwiftPM-first and already builds the desktop executable.
SwiftPM on the current ARM build host successfully cross-built
`x86_64-apple-macosx14.5` using an isolated scratch path. The smallest change
is to build both triples, merge the two app executables with Apple's native
`lipo`, then run the existing app bundle signing and package steps once.

This avoids two product targets, two app identities, architecture-specific
website logic, and a permanent source fork.

## Decision 3: Keep the current installer container in this slice

The repository already has a working `pkgbuild`/`productbuild` app-only install
flow and active local validation around it. A future move to a DMG or ZIP can
be evaluated separately; combining that migration with Intel support would
make release failures harder to attribute.

## Decision 4: Make the build fail closed

The build must not infer success from the compiler exit code alone. It must
inspect both source executables and the final packaged app, require exactly the
expected `arm64` and `x86_64` slices, and reject stale driver component or
distribution references. Signing and notarization remain release gates rather
than local ad-hoc build requirements.

Apple's notarization guidance requires distribution signing, hardened runtime,
secure timestamps, and validation of all distributed executable code.

Source: [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

## Decision 5: Do not use browser architecture detection

The universal installer makes architecture detection unnecessary. The public
page will keep one static download link and remain functional without
JavaScript, user-agent parsing, or client hints. This also prevents a browser
signal from selecting the wrong artifact for someone downloading on behalf of a
different Mac.

## Compatibility boundary

The current product minimum remains macOS 14.5. Intel support therefore means
Intel Macs capable of running that macOS minimum, not every historical Intel
Mac. Product copy and installer checks must state this boundary truthfully.
