# Recording Input Classification Check

## Purpose

Verify the fail-closed microphone-input policy used by the current app-owned
recording source.

## Required Scenarios

| Input class | Expected result |
|---|---|
| Built-in microphone | Accepted when available |
| Wired or USB microphone | Accepted when available |
| Bluetooth or AirPods-class microphone | Accepted when macOS reports an available input |
| Aggregate or multi-output device | Rejected as unsupported input |
| Other virtual input | Rejected as unsupported input |
| Unknown or disconnected input | Rejected with truthful recovery guidance |

## Acceptance

- The policy uses device class and availability, not a product-specific name or
  identifier.
- Rejected inputs cannot silently fall back to an unproven source.
- Permission and unavailable-device failures remain distinguishable.
- Metadata-only evidence contains no raw audio or private device identifiers.
