# Active Call Update Deferral (US4 / Infra Guardrails)

## Purpose

Validate installer update safety under live-call and live-capture conditions, and ensure
the update path returns explicit operator-facing results when it cannot proceed immediately.

## Preconditions

- Active meeting call is running with a physical output selected and route verification state stable.
- Virtual devices are present and app is in `ready` or `active` state.
- Update mode is executed through the interactive installer path (`update-preflight.sh`).

## Scenarios

1. **Active call while update is requested**
   - Start a browser meeting with `2brain Rec` virtual devices routing.
   - Trigger update.
   - Confirm result is explicit `deferred_active_call` (or equivalent) and not a forced reinstall.
   - Confirm no virtual-device artifacts are removed mid-call and no immediate stop is forced.

2. **Active capture restart flag path**
   - Ensure capture state is `active` with one visible local stop action.
   - Trigger update.
   - Confirm user-visible copy: one-action stop remains primary remedy and capture continues until user resolves.
   - Confirm repeated attempts return the same deferral contract until active state clears.

3. **Deferred recovery after call ends**
   - End call/capture.
   - Trigger update again.
   - Confirm update executes or transitions to a deterministic restart-required/installed result.

4. **Override path (optional operator-only flag)**
   - With explicit operator override enabled, confirm deferral is bypassed only when documented and auditable.
   - Confirm override is still visible in logs/reports and does not mutate route state silently.

## Expected Outcome

- Deferral is explicit, truthful, and conservative.
- No capture interruption or forced route mutation occurs during active call.
- Update result reporting distinguishes: deferred, succeeded, and retry-successful.
