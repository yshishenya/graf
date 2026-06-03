# Contract: Local Recording Writer

## Purpose

Define the app-owned writer behavior for persisting local mic and remote speaker
tracks from the existing shared memory audio surface.

## Inputs

- Capture session id.
- App-owned recording directory.
- Shared memory source for local mic frames.
- Shared memory source for mirrored remote speaker capture frames.
- Manual start and stop events from the visible recording controller.

## Outputs

- One local mic track artifact.
- One remote speaker track artifact when remote frames are available.
- One manifest file.
- Metadata-only persistence evidence.

## Runtime Rules

- Writer starts only after manual recording prerequisites pass.
- Writer runs outside HAL/Core Audio callbacks.
- Writer never performs network calls or external egress.
- Writer finalizes on user stop, failure, app shutdown, or fail-closed recovery.
- Writer must not stop non-recording passthrough after finalization.

## Failure Rules

- Directory creation failure blocks recording or fails closed before active
  persisted recording is claimed.
- Empty required track finalizes as `missing` or `degraded`, not `saved`.
- File write or finalization failure marks the affected track `failed`.
- Any failed or missing required track prevents complete recording acceptance.

## Realtime Safety

The writer must not add file IO, allocation, logging, lock waits, process
launches, UI work, or network calls to HAL/Core Audio callbacks.
