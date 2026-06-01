# Install, Update, And Repair Release-Hardening Check

## Purpose

Record metadata-only evidence that install, update, and repair return the driver
to a truthful installed runtime state without hidden manual cleanup.

## Steps

- [ ] Build the local installer package.
- [ ] Install or update the package.
- [ ] Restart `coreaudiod` if required by the operation.
- [ ] Run `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe`.
- [ ] Run repair through `apps/macos/Installer/Scripts/repair.sh` or record why
  repair is not accepted in this environment.
- [ ] Record operation, pre-state, post-state, Core Audio refresh requirement,
  runtime probe result, and final result.

## Evidence Rules

- Results are `passed`, `blocked`, or `not_accepted`.
- Hidden manual cleanup is not accepted.
- Evidence must not contain raw audio, transcript text, credentials, tokens,
  signed URLs, passwords, or meeting content.
