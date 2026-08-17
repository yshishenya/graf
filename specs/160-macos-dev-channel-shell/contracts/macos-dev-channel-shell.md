# Native Contract: macOS Dev Channel and Home

## Dev bundle

- Display name: `GRAF Dev`
- Installed path: `/Applications/GRAF Dev.app`
- Bundle ID: stable `pro.2brain.graf.dev`
- Main executable: native Mach-O `Contents/MacOS/GRAF`; do not use a shell
  launcher as `CFBundleExecutable`, because TCC must evaluate the signed app
  identity and its entitlements at the bundle boundary.
- Local origin: explicit `http://127.0.0.1:<port>` or `localhost:<port>`
- Signing identity: named stable local identity; ad-hoc or mismatched identity
  fails closed.
- Sparkle: no `SUFeedURL`, `SUPublicEDKey`, or production updater start.
- Storage: channel-specific `GRAF Dev` application-support namespace.
- Environment: loopback and channel values are provided through the bundle's
  `LSEnvironment`; inherited local credentials are blanked for Dev.

## Native controls

- Back/Forward/Reload retain current safe route-policy guards.
- Home has a stable accessibility identifier, label “Домой”, tooltip, disabled
  state on canonical list, and loads `DesktopCabinetWorkspace.defaultRoute()`.
- Home never loads an external URL or forwards desktop headers to an external
  origin.

## Permission truth

The contract preserves user-granted status for a same-identity update and
explicitly treats changed identity or user revocation as a new permission
decision. No TCC mutation or workaround is permitted.
