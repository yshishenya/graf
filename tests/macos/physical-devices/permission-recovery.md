# Permission Recovery Scenarios (US3)

## Purpose

Validate recovery behavior when microphone or capture permissions are denied or revoked.

## Scenarios

1. Start audio capture readiness flow with microphone permission denied.
   - Verify Audio Health shows permission-specific copy and recovery action.
   - Verify capture UI refuses `ready` until permission is granted.

2. Grant permission from System Settings and return to the app.
   - Verify permission state updates without restarting the app process.
   - Verify route verification can be retried.

3. Revoke permission after permission was previously granted.
   - Verify recovery action appears and route state transitions to a permission failure family.
   - Verify `ready` is blocked and one-action stop remains visible if capture was running.

4. Attempt capture on unsupported host policy and verify explicit copy.

## Expected Outcome

- Permission failures are explicitly distinguished from route/driver failures.
- Recovery actions are truthful and not mixed with driver-install failure copy.

## Evidence

- Screenshot of permission copy for each blocked state.
- Timestamped Audio Health lines from logs/diagnostic manifest.
- Recovery action selected and executed by user.
