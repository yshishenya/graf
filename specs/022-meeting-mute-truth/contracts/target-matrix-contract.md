# Contract: First Mute-Truth Target Matrix

## Matrix Rows

| Target | Target ID | Product Pause/Stop | Meeting-App Mute Adapter | First Matrix Status | Allowed Release Claim |
|--------|-----------|--------------------|--------------------------|---------------------|-----------------------|
| Zoom native | `zoom_native` | Required | Not supported | `pause_validated` | 2brain Pause/Stop keeps local speech out; Zoom mute is unproven |
| Chrome + Telemost | `chrome_telemost` | Required | Not supported | `pause_validated` | 2brain Pause/Stop keeps local speech out; Telemost/browser mute is unproven |
| Opera + Telemost | `opera_telemost` | Required | Not supported | `pause_validated` | 2brain Pause/Stop keeps local speech out; Telemost/browser mute is unproven |
| Yandex Browser + Telemost | `yandex_telemost` | Deferred/manual evidence only | Not supported | `deferred` | No meeting-app mute-respecting claim |
| Generic or unknown meeting target | `unknown` | Limitation copy required | Not supported | `unsupported` | No meeting-app mute-respecting claim |

## Validation Rules

- Every matrix row must produce metadata-only evidence.
- Rows marked `pause_validated` must prove product-owned Pause/Stop behavior and
  limitation copy.
- Rows marked `deferred` or `unsupported` must not pass release validation as
  meeting-app-mute-respecting.
- Target display names must not include private meeting names or user content.

## Future Adapter Rule

A future target adapter may change `meetingAppMuteAdapterSupported` only through
a separate spec, plan, QA matrix, and privacy/security review. The adapter must
provide fresh metadata-only evidence and must still preserve product-owned
Pause/Stop.
