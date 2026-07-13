# Contract: Existing Local Proof Installation

Repository retirement and host cleanup are separate states.

## Normal build/test/install behavior

- MUST NOT inspect broad system paths beyond read-only validation explicitly
  requested by an operator.
- MUST NOT remove a HAL bundle.
- MUST NOT restart `coreaudiod`.
- MUST NOT add a postinstall migration for historical proof components.
- MUST NOT report the host as clean solely because source code was deleted.

## Deliberate operator cleanup

Published guidance MUST require the operator to:

1. Inspect the exact known historical bundle path and bundle identifier.
2. Stop active recording/call use before any privileged action.
3. Remove only the confirmed historical proof component with explicit
   administrator authorization.
4. Restart the affected audio service or the Mac only as a deliberate follow-up
   when needed.
5. Re-check that current GRAF app data and the app-only installation remain.

This feature does not execute those actions. Any automated migration must be a
separate approved release/deploy slice with rollback and real-hardware proof.
