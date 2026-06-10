# Issue #234 Live Publication Evidence

Date: 2026-06-08

## 2026-06-08 Revalidation Update

Status: closed as superseded / not accepted as driver release evidence.

Follow-up revalidation after commit `63ac726` found that the attempted live
publication strategy is still unsafe. Both variants below can drive
`coreaudiod` into high CPU or probe timeout states:

- stable virtual device publication with hidden/default/StartIO gating;
- app-side armed publication heartbeat before a physical bridge is opened.

Rollback decision:

- keep the driver in fail-closed mode when there is no trusted app heartbeat;
- do not count this evidence as accepted driver release evidence;
- close T060/T061/T062 as superseded for MVP recording by accepted feature
  `025-system-audio-capture-pivot`;
- keep future driver/virtual-device publication work parked until a new
  advanced-routing strategy is designed and validated without CoreAudio CPU
  runaway;
- do not run repeated runtime publication probes on a user machine until the
  HAL surface is changed and bounded with safer diagnostics.

Safe post-rollback baseline observed after reinstalling a fail-closed local
package and restarting CoreAudio:

```text
coreaudiod: 0.0%-1.6% CPU after restart/settle
Core Audio Driver (2brainRecProof.driver): 0.0% CPU
runtime-device-probe --expect-hidden-safe-surface: ACCEPTED immediately after safe reinstall
hal-io-probe --expect-start-blocked-no-heartbeat: ACCEPTED immediately after safe reinstall
```

Important: later repeated hidden-safe probe attempts still caused CoreAudio CPU
spikes, so the probe itself must not be used as release evidence until #234 is
redesigned. Treat the earlier accepted results below as historical debugging
evidence, not final acceptance.

## 2026-06-10 Superseded Closure

- GitHub issue #234 is closed as superseded by accepted feature
  `025-system-audio-capture-pivot`.
- The original driver live-publication objective is not fixed and not accepted;
  it is parked for future advanced-routing work.
- MVP recording no longer depends on live virtual-device publication because
  `025` records microphone plus incoming/system audio directly and has accepted
  final evidence gates.

## Scope

GitHub issue: https://github.com/yshishenya/crisp/issues/234

This evidence covers the HAL publication safety fix for `2brain Rec Microphone`
and `2brain Rec Speaker`. It proves safe idle behavior, explicit-route
publication, HAL I/O callbacks, and fail-closed behavior after route shutdown.

It does not claim the 30-minute or 75-minute release gates. Telemost/browser
manual target validation remains pending in T060/T061.

## Change Summary

- The HAL plugin keeps the virtual device object IDs stable in owned objects,
  device list, and UID translation.
- Public usability is still gated by the app heartbeat through hidden/default
  and StartIO checks.
- `Run Check` and `--start-passthrough` now start the explicit route before
  running readiness checks.
- Graceful app termination clears the route heartbeat through the app lifecycle
  delegate.

## Build And Contract Validation

```sh
make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
swift build --package-path apps/macos -c release --product TwoBrainRecApp
swift run --package-path apps/macos ContractValidation
swift test --package-path apps/macos
```

Result: passed.

## Installed App Verification

The local installer was built with `TWO_BRAIN_REC_VERSION=0.1.234` to avoid the
same-version receipt reinstall issue observed with `0.1.0`.

Installed app hash matched the staged app hash:

```text
0106d3c0337beed737f635fd013aea29a40c37388e21c09e4e9b7ccac376a61e
```

Installed app strings included `explicit_passthrough_ready` and
`passthrough_bridge_stopped`, and did not include
`readiness_check_route_start_skipped`.

## Idle No-Heartbeat Evidence

After CoreAudio restart and app shutdown:

```text
coreaudiod: 0.0% CPU
Core Audio Driver (2brainRecProof.driver): 0.0% CPU
```

```sh
apps/macos/AudioDriver/.build/proof/runtime-device-probe --expect-hidden-safe-surface
apps/macos/AudioDriver/.build/proof/hal-io-probe --expect-start-blocked-no-heartbeat
```

Result: both probes accepted. `2brain Rec Microphone` and
`2brain Rec Speaker` were missing from the user-visible device list and StartIO
was blocked without heartbeat.

## Explicit Route Evidence

Command:

```sh
open -n "/Applications/2brain Rec.app" --args --start-passthrough
```

App log:

```text
event=passthrough_bridge_started detail=explicit route engine active
event=explicit_passthrough_ready summary=Ready for audio routing ... virtualMic=available virtualSpeaker=available ... micRoute=passed ... speakerRoute=passed passthrough=healthy
```

Runtime probe:

```text
2brain Rec Microphone: FOUND hidden=0 alive=1 running=0
2brain Rec Speaker: FOUND hidden=0 alive=1 running=0
Runtime Core Audio publication proof: ACCEPTED
```

HAL I/O probe:

```text
2brain Rec Microphone: callbacks=188 frames=96256 realtime_safety_violations=0
2brain Rec Speaker: callbacks=188 frames=96256 realtime_safety_violations=0
HAL I/O probe: ACCEPTED
```

Active-route CPU sample:

```text
coreaudiod: 10.9%-15.7% CPU
Core Audio Driver (2brainRecProof.driver): 0.0% CPU
2brain Rec.app: 0.1%-0.4% CPU
```

No CoreAudio CPU runaway or probe timeout was observed during this explicit
route probe.

## Shutdown Evidence

Graceful quit:

```sh
osascript -e 'tell application "2brain Rec" to quit'
```

App log:

```text
event=passthrough_bridge_stopped detail=route engine cleared app IO heartbeat
```

Post-quit probes accepted hidden-safe and no-heartbeat StartIO-blocked state.

Forced kill:

```sh
pkill -x "2brain Rec"
```

Immediate post-kill checks may remain open until the 5-second app heartbeat
timeout expires. After the heartbeat timeout, hidden-safe and no-heartbeat
StartIO-blocked probes accepted, with `coreaudiod` and the driver at `0.0%`
CPU.

## Remaining Manual Gate

This evidence does not prove that Telemost or supported browser targets can
select and sustain the virtual devices for T060/T061 duration gates. Those
manual acceptance runs must still be recorded before claiming release
acceptance for `019`.
