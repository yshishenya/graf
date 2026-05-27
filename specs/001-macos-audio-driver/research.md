# Research: macOS Virtual Audio Driver MVP

## Decision: Use a Core Audio virtual-device spike as the primary Phase 0 proof

**Decision**: Prove the MVP using a Core Audio virtual audio component that can
publish user-selectable `2brain Rec Microphone` and `2brain Rec Speaker`
devices, route mic audio to meeting targets, receive speaker audio from meeting
targets, mirror speaker audio for capture, and preserve live passthrough without
backend availability.

**Rationale**: The product requirement is not generic audio processing; it is a
botless, app-selectable macOS audio route. Apple documents Core Audio as the
macOS audio infrastructure and HAL as the layer for real-time audio access, and
Apple documents Audio Server Plug-in callbacks such as `StartIO` for device I/O.
This matches the required device-publication and route-control shape better than
an app-only screen/audio capture approach.

**Primary source references**:

- Apple Core Audio overview: https://developer.apple.com/library/content/documentation/MusicAudio/Conceptual/CoreAudioOverview/WhatisCoreAudio/WhatisCoreAudio.html
- Apple AudioServerPlugIn `StartIO`: https://developer.apple.com/documentation/coreaudio/audioserverplugindriverinterface/startio
- Apple DriverKit overview: https://developer.apple.com/documentation/driverkit
- Apple AudioDriverKit sample: https://developer.apple.com/documentation/audiodriverkit/creating-an-audio-device-driver

**Alternatives considered**:

- App-only capture: rejected for MVP because it cannot provide the required
  meeting-target-selectable virtual microphone and speaker routes and would
  conflict with the constitution's no no-driver fallback rule.
- System loopback-only capture: rejected because it risks remote-to-mic loopback
  and does not provide the explicit two-device route model required by the spec.
- AudioDriverKit first: retained as an alternative if Phase 0 proves it better
  satisfies Apple-supported distribution and entitlement requirements. It must
  not be selected blindly because the MVP needs virtual app-selectable endpoints,
  not a physical device driver replacement.

## Decision: Keep the driver/audio component thin

**Decision**: The driver/audio component owns only virtual device behavior,
real-time passthrough, routing, mirroring, track timing, and continuity/dropout
signals. The desktop app owns capture session state, buffer policy, upload
readiness, retention/purge state, visible UX state, diagnostics packaging, and
audit hooks.

**Rationale**: Real-time audio code must stay small and predictable. Moving
policy, storage, uploads, and diagnostics packaging out of the audio component
reduces crash risk, makes deletion accounting easier, and matches the user's
clarification.

**Alternatives considered**:

- Driver owns buffering and upload: rejected because it mixes real-time audio
  with non-real-time product policy and makes security/deletion accounting harder.
- Desktop app owns all audio routing: rejected because the feature requires
  user-selectable virtual devices and robust passthrough.

## Decision: Use explicit route verification before `ready`

**Decision**: `ready` is allowed only after both mic and speaker routes pass
synthetic verification and the current release candidate has at least one
approved real browser meeting validation path for the target family.

**Rationale**: A purely synthetic signal can prove local graph wiring but cannot
prove browser behavior. A real browser meeting can prove target behavior but is
too slow and fragile for every local readiness check. Both are needed.

**Alternatives considered**:

- Synthetic-only readiness: rejected because browser-specific device behavior
  may still fail.
- Real-meeting-only readiness: rejected because it makes onboarding slow and
  difficult to repeat.

## Decision: Package through an interactive signed/notarized installer

**Decision**: MVP distribution is an interactive installer package with explicit
install, update, repair, rollback, and uninstall outcomes. Silent install, MDM,
fleet deployment, and enterprise deployment are out of scope.

**Rationale**: macOS audio components and helper artifacts need clear user
authorization and trustworthy distribution. Apple documents notarization for
Developer ID-distributed apps, plug-ins, disk images, and flat installer
packages; the MVP should use that distribution model rather than bypassing it.

**Primary source reference**:

- Apple notarization overview: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution

**Alternatives considered**:

- Unsigned internal package: rejected because it creates install friction and
  weakens private-alpha trust.
- Silent/MDM install: rejected by clarification and out of scope for MVP.

## Decision: Treat local capture storage as desktop-owned encrypted artifacts

**Decision**: The desktop app records local buffer artifacts with session ID,
track role, size, age, retention deadline, upload readiness, finalization state,
and purge state. The driver/audio component only emits frames and timing signals;
it does not own persistence.

**Rationale**: The PRD requires seven-day local buffer accounting and truthful
deletion boundaries. These are product lifecycle concerns and belong with the
desktop app and later server synchronization, not the real-time audio component.

**Alternatives considered**:

- Driver-level persistence: rejected for real-time risk and lifecycle opacity.
- No local persistence when offline: rejected because passthrough and capture
  must survive backend/network outages without silent loss.

## Decision: Diagnostics are manifest-based and redacted by default

**Decision**: Support diagnostics are structured manifests containing versions,
states, event IDs, timings, device categories, failure reasons, redaction status,
and recovery outcomes. They must not contain raw audio, transcript text,
credentials, tokens, signed URLs, or secret paths by default.

**Rationale**: Driver failures require actionable diagnostics, but the product
handles meeting content and secrets. A manifest-first diagnostic contract allows
support without turning diagnostics into hidden data egress.

**Alternatives considered**:

- Full logs by default: rejected because logs can contain sensitive data.
- No diagnostics: rejected because driver onboarding and support would be too
  slow for internal alpha.

## Decision: Use two acceptance tracks for QA

**Decision**: QA is split into an automated/synthetic route track and a manual
real-world matrix track covering browser targets and physical device classes.

**Rationale**: Audio driver correctness depends on OS version, device class,
browser target, and call duration. Automated tests catch regressions quickly;
manual matrix runs prove the combinations that matter for release.

**Alternatives considered**:

- Manual-only QA: rejected because regressions would be slow to isolate.
- Automated-only QA: rejected because browser meetings and Bluetooth/AirPods
  behavior need real device coverage.
