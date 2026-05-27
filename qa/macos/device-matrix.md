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

## Release Candidate Thresholds

- Wired audio: local and remote tracks aligned within 100 ms over 60 minutes.
- Wired audio: dropped frames below 0.1%.
- Bluetooth and AirPods-class audio: dropped frames below 0.5% while passthrough remains usable.
- Backend/network outage for 5 minutes must not interrupt live passthrough.
