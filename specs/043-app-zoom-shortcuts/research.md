# Research: App Zoom Shortcuts

## Decision: Implement zoom in the macOS host, not in the server/web cabinet.

**Rationale**: The user asked for application shortcuts while the current app
embeds the meeting workspace inside a native macOS shell. Host-owned zoom keeps
keyboard behavior consistent with macOS, avoids backend changes, and preserves
the existing route allowlist and auth headers. It also lets native recording
controls remain outside the scaled surface.

**Alternatives considered**:

- Server-side CSS preference: rejected because it would require web cabinet
  changes and would not naturally capture app-level keyboard shortcuts.
- Full-window SwiftUI scaling: rejected because it would also scale Record/Stop,
  upload truth, and local audio readiness controls.
- Browser-style per-page zoom UI: rejected as out of scope for this
  keyboard-first slice.

## Decision: Use the existing AppKit lifecycle for menu keyboard commands.

**Rationale**: The app starts `NSApplication` manually through
`AppLifecycleDelegate`, not a SwiftUI `App` scene. Installing an application
menu and target/action handlers in the delegate is the narrowest route for
Command-Plus, Command-Equals, Command-Minus, and Command-0. It avoids forcing a
large entrypoint rewrite.

**Alternatives considered**:

- SwiftUI `.commands`: rejected for this slice because the current entrypoint is
  not a SwiftUI `App` scene.
- Hidden SwiftUI buttons with keyboard shortcuts: rejected because command menu
  discoverability and app-wide keyboard routing belong in the desktop menu
  layer.

## Decision: Store a bounded local numeric preference.

**Rationale**: A zoom factor is local desktop comfort state. A conservative
range of 80% to 140% in 10% steps gives useful readability control without
making the embedded workspace unusable. Invalid values should fall back to
100%.

**Alternatives considered**:

- Unbounded floating-point zoom: rejected because repeated shortcuts could make
  content inaccessible.
- Server profile preference: rejected because no cross-device product behavior
  was requested and server storage would broaden privacy and API scope.

## Decision: Validate with XCTest model and bridge tests before manual smoke.

**Rationale**: The zoom model, clamping, reset, persistence fallback, and
native-shell boundary are deterministic and can be tested without a live cabinet
or production data. A small WebKit bridge helper can expose the applied zoom
factor for tests without requiring a loaded remote page.

**Alternatives considered**:

- Manual-only verification: rejected because shortcut and clamping regressions
  should be caught locally.
- Production cabinet E2E as the primary gate: rejected because this feature does
  not require production data and must remain metadata-safe.
