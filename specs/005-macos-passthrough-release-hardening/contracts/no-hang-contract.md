# Contract: Core Audio No-Hang Evidence

## Target Surfaces

Required release-hardening targets:

- macOS Sound settings
- Chrome audio/device settings or meeting settings
- Opera audio/device settings or meeting settings
- Zoom audio settings
- Yandex Telemost audio settings

Yandex Browser may be recorded as `not_accepted` when explicitly skipped.

## Acceptance Fields

- `target_surface`
- `opened_within_seconds`
- `coreaudiod_cpu_peak_percent`
- `coreaudiod_cpu_sustained_percent`
- `route_state_before`
- `route_state_after`
- `result`
- `failure_reason`

## Thresholds

- Target surface should become usable within 5 seconds.
- During no-call idle, `coreaudiod` must not sustain CPU above 10% for more
  than 30 consecutive seconds.
- The app must not claim live route readiness from device visibility alone.
