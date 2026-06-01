# macOS Device Matrix

## Purpose

Track official MVP coverage for physical audio devices and macOS versions.

## Operating Systems

| OS | CPU | Status | Notes |
|---|---|---|---|
| macOS 14.5 | Apple Silicon | Planned | Minimum supported MVP baseline |
| Latest stable macOS at RC | Apple Silicon | Planned | Validate again before release candidate |
| Any Intel macOS | Intel | Unsupported | Out of MVP scope unless later release decision changes it |

## Physical Audio Classes

| Class | Official MVP Support | Required Coverage |
|---|---:|---|
| Built-in microphone/speakers | Yes | Synthetic route, browser meeting, 60-minute run |
| Wired headset | Yes | Synthetic route, browser meeting, 60-minute run |
| USB microphone | Yes | Synthetic route, browser meeting, 60-minute run |
| USB headset | Yes | Synthetic route, browser meeting, 60-minute run |
| Bluetooth headset | Yes | Synthetic route, browser meeting, 60-minute run |
| AirPods-class device | Yes | Synthetic route, browser meeting, 60-minute run |
| Other devices | Best effort | Must not be marketed as officially supported |

## US1 Route Verification Coverage

| Scenario | Required Result | Evidence |
|---|---|---|
| Fresh install on macOS 14.5 Apple Silicon | Driver installs interactively or reports `requires_restart` | `tests/macos/installer-recovery/fresh-install.md` |
| Virtual microphone publication | `2brain Rec Microphone` visible with input channels only | `tests/macos/route-synthetic/mic-route-check.swift` |
| Virtual speaker publication | `2brain Rec Speaker` visible with output channels only | `tests/macos/route-synthetic/speaker-route-check.swift` |
| Self-routing attempt | Selecting a 2brain Rec virtual device as physical input/output is rejected | `SelfRoutingGuard` contract coverage |
| Route readiness | `ready` shown only after mic and speaker synthetic routes pass | `RouteVerificationContractTests` |

## Release Candidate Thresholds

- Wired audio: local and remote tracks aligned within 100 ms over 60 minutes.
- Wired audio: dropped frames below 0.1%.
- Bluetooth and AirPods-class audio: dropped frames below 0.5% while passthrough remains usable.
- Backend/network outage for 5 minutes must not interrupt live passthrough.

## 005 Route Recovery Evidence

| Scenario | Required 005 result semantics | Evidence |
|---|---|---|
| Physical microphone change | `stale`, `degraded`, or ready only after fresh route evidence within 5 seconds | `tests/macos/physical-devices/aggregate-multi-output-route.md` |
| Physical output change | `stale`, `degraded`, or ready only after fresh route evidence within 5 seconds | `tests/macos/physical-devices/aggregate-multi-output-route.md` |
| Aggregate or multi-output route | `passed`, `blocked`, or `not_accepted`; no release-ready state from visibility alone | `tests/macos/physical-devices/aggregate-multi-output-route.md` |
| Bluetooth route | Managed pilot, `blocked`, or `not_accepted` unless separately proven | `tests/macos/physical-devices/aggregate-multi-output-route.md` |
| Stale browser device ID | `blocked` or `not_accepted` until safe reselection/recovery is recorded | `tests/macos/browser-meetings/stale-device-id-recovery.md` |
| `coreaudiod` restart | Route becomes stale/degraded/blocked or ready only after valid evidence | `tests/macos/installer-recovery/coreaudiod-release-hardening-recovery.md` |
| Sleep/wake | Ready after evidence or truthful stale/degraded/repair state | `tests/macos/physical-devices/sleep-wake-release-hardening.md` |
