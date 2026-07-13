# Recording-Assisted Acceptance

This is the long-duration acceptance gate for the current app-owned recording
architecture. It is separate from the short manual start/stop smoke.

## Preconditions

- [ ] Product retention and deletion copy is current.
- [ ] Evidence handling forbids uncontrolled audio/content egress.
- [ ] The current-build short recording smoke passes first.

## Required Evidence

- [ ] Long-duration replay covers the app-owned microphone source.
- [ ] Long-duration replay covers the app-owned system-audio source.
- [ ] The two original tracks remain separate and playable.
- [ ] Dropouts, timing discontinuities, and source loss are recorded truthfully.
- [ ] One-action `Stop` finalizes or fails closed.
- [ ] Sleep/wake, permission changes, and eligible microphone changes do not
  create a false successful package.
- [ ] Upload, transcription, MediaScribe, and Langfuse behavior matches the
  separately accepted policies.

## Current Status

Open. Removing the retired routing implementation does not itself accept this
gate. A fresh long-duration run on the current build is still required.
