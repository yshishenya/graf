# Audio Settings No-Hang Matrix

This matrix records metadata-only evidence for the 005 pre-recording hardening
slice. It does not record audio, transcript text, meeting content, credentials,
tokens, signed URLs, or screenshots with meeting content.

## Targets

| Target surface | Required outcome | Current status | Notes |
|---|---|---|---|
| macOS Sound settings | Usable within 5 seconds or blocked/not accepted | Pending | May be launched by helper when UI no-hang mode is enabled |
| Chrome audio settings | Usable within 5 seconds or blocked/not accepted | Pending | Browser target; no meeting content required |
| Opera audio settings | Usable within 5 seconds or blocked/not accepted | Pending | Browser target; no meeting content required |
| Zoom audio settings | Usable within 5 seconds or blocked/not accepted | Pending | App may be absent and recorded as not accepted |
| Yandex Telemost audio settings | Usable within 5 seconds or blocked/not accepted | Pending | Browser target; no meeting content required |

## Evidence Fields

- `target_surface`
- `opened_within_seconds`
- `coreaudiod_cpu_peak_percent`
- `coreaudiod_cpu_sustained_percent`
- `route_state_before`
- `route_state_after`
- `result`
- `failure_reason`

## Rules

- Skipped or unavailable targets are `not_accepted`, not `passed`.
- A target that hangs or exceeds the 5-second usability threshold is `blocked`.
- `coreaudiod` sustained CPU above 10% for more than 30 consecutive seconds is
  a blocking release-hardening failure.
- Device visibility alone is not live audio readiness.
