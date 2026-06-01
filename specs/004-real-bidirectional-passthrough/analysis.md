# Spec Kit Analysis: Stabilization Pass

Date: 2026-06-01

Scope: `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, runtime probe
contract, validation script, and Phase 7 stabilization changes.

## Result

No open critical or high Spec Kit blockers remain in the stabilization slice
after the 2026-06-01 review fixes.

Final live-route acceptance remains intentionally pending for physical
microphone, physical speaker, browser target, latency, leakage, no-loopback,
and final fail-closed evidence. Synthetic checks and Core Audio surface probes
must not be used as substitutes for those acceptance gates.

## Findings Resolved

| ID | Severity | Location | Resolution |
| --- | --- | --- | --- |
| A1 | Critical | `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` | Speaker callback now zero-fills `ioData` when Core Audio requests more frames than the preallocated scratch buffer can hold. |
| A2 | Critical | `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` | Non-atomic Swift callback counters were removed from realtime AudioUnit callbacks. The static RT safety check now rejects reintroduction of those counters. |
| A3 | High | `apps/macos/AudioDriver/Sources/Proof/RuntimeDeviceProbe.cpp` | Removed the impossible `--expect-live-running` expectation. Runtime probe modes now cover `default-safe`, `non-running-surface`, and `visible-alive-surface`, with explicit output that surface state is not measured live audio acceptance. |
| A4 | High | `apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` | Automatic non-recording startup validation now runs unconditionally in the main validation script. |
| A5 | Critical | `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift` | `verifyLiveReadiness` no longer fabricates live-ready evidence from synthetic route probes. Synthetic pass now maps to blocked/stale live readiness until measured live-route evidence exists. |
| A6 | High | `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift` | Route engine start/stop/state ownership is now in a service object outside SwiftUI. The SwiftUI-facing `ExperimentalPassthroughCoordinator` only mirrors service state and forwards explicit commands. |
| A7 | High | `apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` | XCTest validation uses `--disable-swift-testing` to avoid the local `swift-testing` helper hang observed after build completion. |

## Coverage Summary

| Requirement/Gate | Has Task? | Task IDs | Status |
| --- | --- | --- | --- |
| Realtime callbacks avoid allocation, logging, file I/O, wall-clock access, and non-atomic mutation | Yes | T067, T075, T081 | Covered by `tests/macos/static/audio-rt-safety-check.sh`; validation pass recorded. |
| Ring buffer writer must not mutate reader index and must reject overflow all-or-nothing | Yes | T069, T070, T071, T072 | Covered by Swift compatibility tests and C++ proof vectors. |
| Default app launch may autostart only non-recording app-side bridge/heartbeat, with virtual devices non-running until client I/O | Yes | T068, T073, T074, T077, T078, T079, T083, T084 | Covered by `default-passthrough-disabled-check.sh` and runtime probe `--expect-default-safe`. |
| Runtime probe distinguishes publication/default/non-running/visible-alive surface states | Yes | T078, T079 | Covered by runtime probe modes; documented as surface-only evidence, not final fail-closed or live-route acceptance. |
| Synthetic checks cannot count as physical/browser acceptance | Yes | T079, T081, T063, T064 | Documented; physical/browser tasks remain pending. |
| Final physical microphone/speaker/browser acceptance | Yes | T063, T064 | Pending by design until measured live-route implementation and evidence exist. |
| Diagnostics redaction | Yes | T065 | Completed after package/runtime proof update; matches were policy/fixture forbidden-field strings only. |

## Validation Evidence

- `sh tests/macos/static/audio-rt-safety-check.sh`: PASS.
- `swift build --package-path apps/macos -c release --product TwoBrainRecApp`: PASS.
- `swift test --package-path apps/macos --disable-swift-testing`: PASS.
- `make -C apps/macos/AudioDriver proof-scaffold-run proof-plugin-build proof-runtime-probe-build proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe`: PASS.
- `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-non-running-surface`: PASS.
- `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-visible-alive-surface`: PASS, surface state only.
- `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh`: PASS.
- Installed automatic non-recording startup check on 2026-06-01: PASS. App log
  recorded automatic route start and ready snapshot; runtime probe remained
  accepted with `running=0` for both virtual devices.
- User acceptance on 2026-06-01: PASS. The installed app/browser flow works
  without pressing `Run Check`; `Run Check` remains recheck/repair only.
- Installed package/runtime proof after `coreaudiod` restart recorded in
  `apps/macos/AudioDriver/RuntimeProofReport.md`: PASS for publication,
  default-safe, non-running surface, and visible/alive surface states.
- Diagnostics redaction scan under `apps/macos`, `tests/macos`, `qa/macos`,
  and `specs/004-real-bidirectional-passthrough`: PASS; matches were
  policy/fixture forbidden-field strings only.

## Remaining Non-Blockers

- Yandex Browser remains intentionally skipped/not accepted by decision for this
  cycle. Chrome, Opera, and Telemost have manual smoke coverage.
- Release hardening should still add broader long-duration call, device-change,
  and OS-version matrix evidence before external distribution.
