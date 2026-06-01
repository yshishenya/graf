# Runtime Core Audio Proof Report

**Status**: ACCEPTED (Core Audio publication only; real passthrough pending)

This report is the required evidence gate before any US1 implementation task
that publishes real virtual devices or installer behavior.

## Live Route Readiness Proof Requirements (003)

The 003 feature does not accept publication alone as route readiness. Runtime
proof must include metadata-only evidence for:

- current private app I/O heartbeat state and public device hidden state;
- microphone valid-frame counters for the selected physical microphone path;
- speaker stimulus counters for the selected physical output path;
- self-routing rejection for virtual devices selected as physical working
  devices;
- aggregate/multi-output routes recorded as managed/blocked unless measurable;
- built-in/wired added latency `<= 30 ms` before release-ready status;
- built-in/wired remote-to-mic leakage `<= -45 dB` and not intelligible before
  release-ready status;
- route invalidation within 5 seconds after physical device, output route,
  browser target, Bluetooth profile, app heartbeat, or `coreaudiod` changes.

Accepted runtime evidence must not include raw audio, transcript text,
credentials, tokens, signed URLs, or meeting content.

## Evidence Requirements

Fill this report only after running the runtime proof on an Apple Silicon Mac.
One machine result unlocks architecture work; it is not release-candidate matrix
coverage.

Required evidence:

- Date:
- Machine:
- CPU architecture:
- macOS version:
- Proof command:
- Build artifact:
- Virtual device publication result:
- `2brain Rec Microphone` visible to macOS:
- `2brain Rec Speaker` visible to macOS:
- Self-routing rejection baseline:
- Passthrough/mirror exercised:
- Continuity signal exercised:
- Permissions/signing/notarization assumptions:
- Known limitations:
- Decision: Core Audio path accepted, rejected, or still blocked.

## Current Result

Runtime Core Audio publication is accepted for the Phase 0 architecture gate.
The proof AudioServerPlugIn bundle was installed into the HAL plug-in directory,
Core Audio loaded it, and the runtime visibility probe observed both required
MVP virtual devices.

- Date: 2026-05-27 16:10:10 MSK
- Machine: MacBook-Pro-7.local
- CPU architecture: arm64
- macOS version: 26.2 (25C56)
- Build command: `make -C apps/macos/AudioDriver proof-plugin-build`
- Install command: direct equivalent of `make -C apps/macos/AudioDriver proof-plugin-install`
- Proof command: `make -C apps/macos/AudioDriver proof-runtime-probe-run`
- Build artifact: `apps/macos/AudioDriver/.build/proof/2brainRecProof.driver`
- Runtime probe artifact: `apps/macos/AudioDriver/.build/proof/runtime-device-probe`
- Virtual device publication result: ACCEPTED; the probe enumerated Core Audio
  devices visible to the current user and found both required virtual devices.
- `2brain Rec Microphone` visible to macOS: Yes
- `2brain Rec Speaker` visible to macOS: Yes
- Self-routing rejection baseline: Not exercised by this publication proof;
  remains a US1 implementation and route-verification task.
- Passthrough/mirror exercised: Not exercised by this publication proof;
  remains a US1/US2 implementation task.
- Continuity signal exercised: Not exercised by this publication proof; remains
  a US2 timing implementation task.
- Permissions/signing/notarization assumptions: The proof bundle was ad-hoc
  signed for local validation only and installed into
  `/Library/Audio/Plug-Ins/HAL`. It is not a release installer, Developer ID
  signature, or notarized package.
- Known limitations: This proof publishes visible devices with minimal silent
  streams. It does not implement production routing, passthrough, buffering,
  self-routing rejection, installer UX, notarization, or track capture.
- Decision: Core Audio publication path is accepted for architecture work. US1
  implementation may start, but production tasks must replace the proof bundle
  with the real signed/notarized driver and route-verification implementation.

## Current Runtime Alignment (2026-05-31)

The desktop app now launches locally when Developer Tools Security is enabled for
ad-hoc development builds. The installed driver package and both virtual devices
are visible to macOS.

Interactive runtime probe evidence from 2026-05-31:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- krisp microphone
- krisp speaker
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: FOUND
- 2brain Rec Speaker: FOUND
Runtime Core Audio publication proof: ACCEPTED
```

## Stabilization Runtime Proof - 2026-06-01 14:47 MSK

Commands executed from repository root after Phase 7 stabilization fixes:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
sudo killall coreaudiod
open -a "2brain Rec"
make -C apps/macos/AudioDriver proof-runtime-probe-run
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-non-running-surface
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-visible-alive-surface
```

Package install result:

```text
installer: Package name is 2brain Rec
installer: Upgrading at base path /
installer: The upgrade was successful.
```

Runtime proof after reinstall and `coreaudiod` restart:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Runtime passthrough evidence: publication-only; this is Core Audio surface state only, not measured live audio acceptance.
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED

Runtime passthrough evidence: default-safe; this is Core Audio surface state only, not measured live audio acceptance.
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED

Runtime passthrough evidence: non-running-surface; this is Core Audio surface state only, not measured live audio acceptance.
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED

Runtime passthrough evidence: visible-alive-surface; this is Core Audio surface state only, not measured live audio acceptance.
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Settle check after restart:

```text
coreaudiod: pid=51943 cpu=0.0 elapsed=00:59
Core Audio Driver (2brainRecProof.driver): running under coreaudiod
Desktop app: no persistent process after default launch; no app-side bridge or
heartbeat was observed.
```

Interpretation: ACCEPTED for installed Core Audio publication, default-safe,
non-running surface, and visible/alive surface evidence. This is not physical
microphone, speaker playback, latency, leakage, no-loopback, browser, or final
live-route fail-closed acceptance evidence.

The app must still report **not ready for calls** because real bidirectional
audio passthrough has not been implemented and verified end to end. Current
readiness checks are intentionally strict:

- virtual microphone visible in macOS: accepted
- virtual speaker visible in macOS: accepted
- physical microphone to virtual microphone audio path: pending
- virtual speaker to physical speaker audio path: pending
- browser/meeting end-to-end call validation: pending

Any UI state, checklist item, or task that suggests production passthrough is
complete is obsolete and must be corrected before release readiness review.

Safety correction added on 2026-05-31:

- high-frequency HAL callback trace is disabled by default and can only be
  enabled through the explicit verbose trace flag;
- proof devices report that they cannot become the system default device while
  passthrough is pending, so a local install should not steal normal system
  input/output.

## Private App I/O Fail-Closed Attempt (2026-05-31 03:43 MSK)

Status: **NOT ACCEPTED for T059**.

The desktop app process was present before the test (`59877`), the runtime
publication probe accepted both virtual devices, the app was terminated, and the
probe was run again after a 6-second wait. The app process was gone, but the
publication probe still found both public virtual devices:

```text
=== after kill: app process ===
=== after kill: runtime probe ===
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- krisp microphone
- krisp speaker
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: FOUND
- 2brain Rec Speaker: FOUND
Runtime Core Audio publication proof: ACCEPTED
```

After relaunch, the app process returned (`60450`) and the publication probe
again accepted both devices.

Decision: this attempt records useful lifecycle evidence, but it does **not**
prove private app I/O fail-closed behavior. Two reasons make it insufficient:

- the command used here proves only Core Audio publication by device name; it
  does not prove that the driver reports the devices hidden or unavailable when
  the app engine heartbeat is gone;
- the locally built package from 2026-05-31 was built but this evidence does not
  show that the updated package was installed before the kill/relaunch test.

Required follow-up: install the freshly built local package, restart Core Audio,
then run a fail-closed probe that checks app I/O availability or hidden state,
not just device-name publication. `T059` remains open until that evidence is
accepted.

## Private App I/O Fail-Closed Attempt (2026-05-31, Updated Package)

Status: **NOT ACCEPTED for T059**.

The local package was rebuilt, installed successfully with `installer`, and
`coreaudiod` was restarted. The app was launched and the strengthened runtime
probe reported both devices as visible, unhidden, and alive:

```text
=== before kill ===
71878
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

After terminating the app and waiting 6 seconds, the app process was gone, but
the strengthened probe still reported both public devices as unhidden:

```text
=== after kill ===
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Decision: this confirmed a real fail-closed defect. The installed driver was
using shared-memory existence as the private app I/O availability signal, so the
devices stayed public after the desktop app exited. The implementation was
changed after this attempt so the app writes a shared-memory heartbeat and the
driver treats app I/O as unavailable when that heartbeat is missing or older
than 5 seconds.

Required follow-up: rebuild and reinstall the package containing the heartbeat
fix, then rerun the kill/relaunch proof. `T059` remains open until the post-fix
probe shows either `MISSING` or `hidden=1` after app termination.

## Private App I/O Fail-Closed Attempt (2026-05-31, Heartbeat Fix)

Status: **NOT ACCEPTED for T059**.

The package containing the shared-memory heartbeat was rebuilt and installed.
After `coreaudiod` restart, the probe reported both devices as missing even
before the app was killed:

```text
=== before kill ===
- 2brain Rec Microphone: MISSING
  hidden=unreadable alive=unreadable running=unreadable
- 2brain Rec Speaker: MISSING
  hidden=unreadable alive=unreadable running=unreadable
Runtime Core Audio publication proof: BLOCKED
```

After app termination and relaunch the devices remained missing. The app process
was present after relaunch (`86902`), but the driver still did not republish the
public devices.

Decision: this attempt confirmed that the fail-closed side is now strict enough,
but recovery is blocked because the app cannot establish or refresh private app
I/O. The likely cause is shared-memory permissions: `coreaudiod` creates the
POSIX shared memory object as root, and umask can leave it not writable by the
desktop app. The driver was updated after this attempt to call `fchmod(...,
0666)` immediately after `shm_open`, so the desktop app can write the heartbeat
needed for recovery.

Required follow-up: rebuild and reinstall the package containing the shared
memory permission fix, then rerun the same kill/relaunch proof. `T059` remains
open until the post-fix probe shows devices available before kill, unavailable
after kill, and available again after relaunch.

## Private App I/O Fail-Closed Attempt (2026-05-31, Permission Fix)

Status: **NOT ACCEPTED for T059**.

The package containing the shared-memory permission fix was rebuilt and
installed. The app launched (`18251` before kill, `18681` after relaunch), but
the runtime probe still reported both public devices as missing before kill,
after kill, and after relaunch:

```text
- 2brain Rec Microphone: MISSING
  hidden=unreadable alive=unreadable running=unreadable
- 2brain Rec Speaker: MISSING
  hidden=unreadable alive=unreadable running=unreadable
Runtime Core Audio publication proof: BLOCKED
```

Decision: fail-closed was still implemented at the wrong Core Audio boundary.
The driver removed devices from `kAudioPlugInPropertyDeviceList` when the app
heartbeat was missing. Core Audio can cache that empty device list and therefore
cannot reliably recover by observing a later heartbeat. The driver was updated
after this attempt so `kAudioPlugInPropertyDeviceList` always returns the stable
virtual device objects, while app I/O availability is expressed through
`kAudioDevicePropertyIsHidden`. This keeps the objects recoverable and lets the
probe observe `FOUND hidden=0` before kill, `FOUND hidden=1` or `MISSING` after
kill, and `FOUND hidden=0` after relaunch.

Required follow-up: rebuild and reinstall the package containing the stable
device-list fix, then rerun the same kill/relaunch proof. `T059` remains open
until that post-fix evidence is accepted.

## Private App I/O Fail-Closed Acceptance (2026-05-31 04:16 MSK)

Status: **ACCEPTED for T059**.

The package containing the stable device-list, shared-memory heartbeat, and
shared-memory permission fixes was installed successfully. `coreaudiod` was
restarted and the app was launched. Before app termination, both virtual devices
were published, visible, unhidden, and alive:

```text
=== before kill ===
29497
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

After terminating the desktop app and waiting beyond the 5-second heartbeat
timeout, both public virtual devices were absent from the current Core Audio
device list:

```text
=== after kill ===
- 2brain Rec Microphone: MISSING
  hidden=unreadable alive=unreadable running=unreadable
- 2brain Rec Speaker: MISSING
  hidden=unreadable alive=unreadable running=unreadable
Runtime Core Audio publication proof: BLOCKED
```

After relaunching the app, both virtual devices returned and were again
unhidden and alive:

```text
=== after relaunch ===
30123
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Decision: private app I/O fail-closed behavior is accepted for this feature
gate. App-engine loss removes the public devices from normal Core Audio
publication, and app relaunch restores publication only after the app can write
a fresh heartbeat into shared memory.

## Passthrough Prototype Scope (2026-05-28 to 2026-05-31)

- Decision: Passthrough scaffolding exists, but production passthrough is not yet
  accepted.
- Implemented/prototyped pieces:
  - shared memory ring buffer bridge between the HAL driver and desktop app:
    `apps/macos/Shared/Sources/SharedAudioMemory.swift` and
    `apps/macos/Shared/CShmHelpers/shm_helpers.c`
  - app-side Core Audio bridge scaffolding:
    `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`
  - driver-side shared memory reads/writes in
    `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`
  - route status model updates in `AudioModels.swift`
- Not accepted yet:
  - `StartIO`/`StopIO` do not yet prove a live physical-device bridge for normal
    calls.
  - The app does not yet run a safe user-visible readiness flow that proves real
    microphone and speaker audio movement.
  - Browser meeting targets have not been validated against the virtual
    microphone and virtual speaker paths.
- Validation completed so far:
  - `swift build --package-path apps/macos -c release --product TwoBrainRecApp`
  - `make -C apps/macos/AudioDriver proof-plugin-build`
  - `sh apps/macos/Scripts/validate-us1-regression.sh`

These commands validate buildability, model behavior, and Core Audio publication
regression coverage. They do not prove production passthrough.

## Local Installer Runtime Acceptance (2026-05-31 06:07 MSK)

Status: **ACCEPTED for 003 runtime publication and fail-closed release
evidence**.

The local package was rebuilt and installed through `installer`. The installer
postinstall path now clears local HAL loading blockers before restarting
`coreaudiod`; no manual postinstall repair was required before running the
runtime probe.

```text
installer: The upgrade was successful.
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Lifecycle proof after the same install:

```text
=== before kill ===
27762 /Applications/2brain Rec.app/Contents/MacOS/2brain Rec
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED

=== after kill ===
- 2brain Rec Microphone: MISSING
  hidden=unreadable alive=unreadable running=unreadable
- 2brain Rec Speaker: MISSING
  hidden=unreadable alive=unreadable running=unreadable
Runtime Core Audio publication proof: BLOCKED

=== after relaunch ===
33368 /Applications/2brain Rec.app/Contents/MacOS/2brain Rec
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Decision: the local installer path, runtime publication proof, and private app
I/O fail-closed lifecycle are accepted for the 003 implementation gate. This is
not production passthrough acceptance: real browser meeting audio, real
microphone-to-virtual-microphone passthrough, and real
virtual-speaker-to-physical-speaker passthrough remain out of scope for this
feature state.

## Real Bidirectional Passthrough Scope (004)

Status: **PARTIALLY ACCEPTED / BROWSER CALL EVIDENCE PENDING**.

Feature 004 moves beyond publication and readiness evidence into real
non-recording bidirectional audio movement:

- selected physical microphone audio must feed `2brain Rec Microphone`;
- audio sent to `2brain Rec Speaker` must play through the selected physical
  output;
- browser calls must remain usable through the two virtual devices;
- recording, upload, transcription, MediaScribe, Langfuse, and new network
  egress remain out of scope;
- private app I/O fail-closed behavior accepted in 003 must remain intact.

Accepted on 2026-05-31 for local package install, runtime publication,
fail-closed driver heartbeat gating, and synthetic passthrough checks.
Physical browser-call evidence remains pending and must not be marketed as
passed until Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser are
run against the installed app.

Validation commands executed:

```text
swift build --package-path apps/macos -c release --product TwoBrainRecApp
swift test --package-path apps/macos
make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build
sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
killall coreaudiod
make -C apps/macos/AudioDriver proof-runtime-probe-run
```

Runtime proof after reinstall and `coreaudiod` restart:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Runtime passthrough evidence: publication and fail-closed state only; live audio path checks run separately.
Expected device visibility:
- 2brain Rec Microphone: FOUND
  hidden=0 alive=1 running=0
- 2brain Rec Speaker: FOUND
  hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

Synthetic passthrough checks accepted:

```text
live-mic-readiness-check: ACCEPTED
live-mic-passthrough-check: ACCEPTED
live-mic-silence-check: ACCEPTED
live-mic-self-routing-check: ACCEPTED
live-speaker-readiness-check: ACCEPTED
live-speaker-passthrough-check: ACCEPTED
live-speaker-failure-check: ACCEPTED
live-passthrough-no-loopback-check: ACCEPTED
live-self-routing-check: ACCEPTED
live-latency-check: ACCEPTED
live-leakage-check: ACCEPTED
live-route-outage-check: ACCEPTED
live-passthrough-outage-check: ACCEPTED
live-passthrough-fail-closed-check: ACCEPTED
```

## Publication Spike Attempt

- Date: 2026-05-27
- Build command: `make -C apps/macos/AudioDriver proof-plugin-build`
- Build artifact: `apps/macos/AudioDriver/.build/proof/2brainRecProof.driver`
- Artifact status: Builds as a Mach-O arm64 bundle and passes ad-hoc code-sign
  verification.
- Exported factory symbol: `_TwoBrainRecProofDriverFactory`
- Initial installation status: `/Library/Audio/Plug-Ins/HAL` is root-owned, so
  installing the proof bundle and restarting `coreaudiod` requires admin
  privileges.
- Follow-up after first manual install: the bundle installed successfully, but
  Core Audio still did not list the proof devices. The installed bundle was
  structurally present and signed, but discovery logs did not show the proof
  bundle being loaded. The proof package now includes an
  `IOPlatformExpertDevice` loading condition and clears extended attributes
  during install before restarting `coreaudiod`.
- Final follow-up: after fixing the AudioServerPlugIn driver reference shape,
  adding empty device control lists, and adding `kAudioDevicePropertyClockDomain`
  responses, Core Audio loaded the proof bundle and published both MVP devices.
- Current decision: ACCEPTED for the Phase 0 Core Audio publication gate.

Observed device list:

```text
Core Audio devices visible to this user:
- Микрофон MacBook Pro
- Динамики MacBook Pro
- 2brain Rec Microphone
- 2brain Rec Speaker
- Многовыходное устройство
Expected device visibility:
- 2brain Rec Microphone: FOUND
- 2brain Rec Speaker: FOUND
Runtime Core Audio publication proof: ACCEPTED
```
