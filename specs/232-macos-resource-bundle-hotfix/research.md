# Research: Безопасный запуск macOS после обновления

## Decision 1: Resolve packaged resources from the application bundle

**Decision**: When `Bundle.main.resourceURL` points at a packaged `.app`, look
for `TwoBrainRecMacOS_TwoBrainRecAppCore.bundle/Resources/meeting-target-registry-baseline.json`
there first. Use `Bundle.module` only for SwiftPM development/test execution.

**Rationale**: The public `.1` binary asks SwiftPM for the generated resource
bundle beside `/Applications/GRAF.app`, while the installer correctly places it
under `Contents/Resources`. `Bundle.module` traps before it can return `nil`.

**Alternatives considered**: Move/copy the resource bundle beside `GRAF.app`
(non-standard and breaks packaging trust); guard every caller (duplicates the
same unsafe accessor); disable meeting detection at startup (changes product
behavior and only masks the cause).

## Decision 2: Missing resource is a degraded feature, not an app crash

**Decision**: Return `nil` when the packaged bundle or baseline file is absent.
The existing `MeetingTargetRegistryStore` remains responsible for cache/remote
fallback and its current unavailable state.

**Rationale**: A registry input must not terminate the entire app. This reuses
the existing recovery contract without a new fallback mechanism.

**Alternatives considered**: Embed a second JSON copy in code (duplicate source
of truth); catch a Swift fatal error (not catchable); invent a default registry
(changes detection policy).

## Decision 3: Validate the exact extracted candidate process

**Decision**: A release smoke accepts an app path, validates its bundle shape,
launches `Contents/MacOS/GRAF` directly, stores `$!`, waits five seconds and
terminates/waits only that PID. It uses a temporary HOME and loopback product
origins to prevent external traffic.

**Rationale**: Process-name lookup can mistake an already-running installation
for the candidate and can kill an unrelated user process. Direct PID ownership
is both smaller and safer.

**Alternatives considered**: `open -a` plus `pgrep` (ambiguous identity), UI
automation (larger and less deterministic), signature-only validation (already
passed for the broken release).

## Decision 4: Publish immutable artifacts in dependency order

**Decision**: Staple the app and PKG, recreate the final ZIP, then generate
checksums/release notes from those final bytes. Upload versioned assets first
and replace the production appcast last.

**Rationale**: Stapling changes bytes. The existing `.1` release demonstrates
that pre-final checksums can disagree with the public artifact.

**Alternatives considered**: Rewrite `.1` assets (destroys historical
provenance); publish appcast before assets (can strand clients on unavailable
or inconsistent bytes).

## Decision 5: Recovery has two paths

**Decision**: Validate a normal Sparkle update from the last healthy public
version and document/install `.2` manually over `.1` for affected users.

**Rationale**: `.1` can crash before Sparkle has time to complete an in-app
update. A trusted Developer ID PKG/ZIP is the deterministic repair path.

**Alternatives considered**: Rely on repeated `.1` launch, cache clearing or
reinstalling `.1`; none changes the crashing binary/resource lookup.
