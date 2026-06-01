# Contract: Low-Resource Route Lifecycle

## Purpose

Define the externally observable route lifecycle between the installed 2brain Rec
virtual devices, the desktop app route engine, diagnostics, and validation
harnesses.

## Readiness Planes

Every readiness report must expose these planes separately:

| Plane | Required Evidence | Must Not Mean |
|-------|-------------------|---------------|
| `publication` | virtual mic/speaker visible, alive, hidden=0 | live audio route is ready |
| `client_io` | explicit Core Audio running/client IO state | audio energy is nonzero |
| `app_bridge` | fresh app heartbeat and bridge readiness | recording is active |
| `physical_devices` | valid non-2brain physical input/output | arbitrary virtual chain is accepted |
| `recording_trigger` | application recording trigger state | driver owns recording |

## States

| State | Meaning | Allowed Next States |
|-------|---------|---------------------|
| `idle_safe` | Devices are visible/fail-closed; no sustained heavy physical route work. | `starting`, `stale`, `blocked` |
| `starting` | Bounded route startup attempt is running. | `ready`, `blocked`, `failed`, `fallback` |
| `ready` | Route evidence is fresh and valid; no hidden recording. | `active`, `stale`, `idle_safe`, `blocked` |
| `active` | Explicit client IO is open and bridge is healthy. | `ready`, `stale`, `idle_safe`, `blocked` |
| `stale` | Prior ready/active evidence was invalidated. | `retrying`, `blocked`, `idle_safe` |
| `blocked` | Route cannot safely start or recover under current conditions. | `retrying`, `fallback`, `idle_safe` |
| `failed` | Startup or recovery failed with a metadata-only reason. | `retrying`, `fallback`, `idle_safe` |
| `retrying` | Bounded retry has been requested or scheduled. | `starting`, `blocked`, `failed` |
| `fallback` | Accepted 005 app-launch lifecycle is restored. | `idle_safe`, `starting` |

## Activation Rules

- Client activity must come from explicit Core Audio IO state (`StartIO` /
  `StopIO`, `DeviceIsRunning`, or deterministic test fixture).
- Natural silence must not stop or downgrade an active route.
- A browser/meeting app opening only microphone or only speaker may activate the
  needed physical side without implying recording.
- Route startup must resolve within 3000 ms as `ready`, `blocked`, `failed`, or
  `fallback`.
- The app must not require the user to press `Run Check` for normal automatic
  passthrough activation.

## Visibility Rules

- Public 2brain Rec virtual devices remain visible and fail-closed by default.
- App exit, stale heartbeat, or idle state must not hide public devices in this
  feature.
- A visible device is not sufficient evidence for live route readiness.

## Physical Device Rules

- 2brain Rec virtual microphone/speaker must be rejected as physical working
  devices.
- Other virtual, aggregate, multi-output, or chained devices are unsupported/not
  release-ready unless later validation explicitly accepts them.
- Built-in and wired physical devices are the release-quality target set.

## Recording Boundary

- Driver route lifecycle must not create recordings, transcripts, uploads,
  MediaScribe jobs, Langfuse traces, analytics, or external egress.
- Future recording must subscribe from application software after an explicit
  application trigger and visible capture state.

## Failure Semantics

- Stale app bridge health downgrades live route readiness and causes driver IO to
  fail closed.
- Slow Core Audio setup or enumeration must surface as `blocked`/`failed`/`fallback`
  within 3000 ms.
- Route truth diagnostics must keep metadata only.
