# Universal Installer Contract

## Build contract

The installer build command produces one app-only package at:

```text
apps/macos/.build/installer/graf.pkg
```

The staged application executable MUST:

- be a valid Mach-O executable;
- contain exactly the native `arm64` and `x86_64` slices;
- declare bundle identifier `pro.2brain.graf`;
- declare minimum macOS `14.5`;
- use the requested CalVer product version;
- contain no legacy driver component or driver package reference.

## Public download contract

The public page MUST expose one primary download link:

```text
/static/public/downloads/graf.pkg
```

The link label MUST describe a universal GRAF installer and MUST NOT ask the
user to choose ARM or Intel.

## Failure contract

The build MUST fail before publication when:

- either architecture build fails;
- either source executable lacks its expected architecture;
- the merged executable lacks either required architecture;
- bundle metadata is inconsistent;
- a driver package or driver reference appears in the app-only installer;
- the final public asset is missing.

## Compatibility contract

An Intel Mac below macOS 14.5 is outside the supported GRAF desktop promise.
The installer and support documentation must report that boundary without
claiming that the universal artifact supports older operating systems.
