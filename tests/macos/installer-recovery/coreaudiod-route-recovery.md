# coreaudiod Route Recovery

## Purpose

Validate recovery after `coreaudiod` restart without falsely preserving stale
readiness.

## Steps

1. Build and install the current local package.
2. Launch `2brain Rec`.
3. Pass live route readiness with physical input and output selected.
4. Restart Core Audio:

   ```sh
   sudo killall coreaudiod || true
   ```

5. Confirm public virtual devices return only when the app heartbeat is present.
6. Confirm prior readiness is stale and requires a user-triggered recheck.
7. Run readiness check again and record pass/fail evidence.

## Acceptance

- Public virtual device recovery follows private app I/O heartbeat state.
- Prior readiness is not silently reused after `coreaudiod` restart.
- Recovery action is visible and diagnostics contain no raw audio or meeting
  content.
