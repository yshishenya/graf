# Research: macOS Passthrough Release Hardening

## Decision: Defer full long-duration manual call replay until recording exists

**Rationale**: Without local recording, long-call verification is mostly
subjective and expensive. Recording will allow replayable evidence for channel
separation, distortion, dropouts, and no-loopback. This slice should avoid
creating brittle manual blockers before the product can capture evidence
truthfully.

**Alternatives considered**:

- Require a 30-minute manual call now: rejected because it is hard to verify
  after the fact and would likely need to be repeated after recording lands.
- Skip all browser smoke evidence: rejected because a short smoke check remains
  useful to ensure the previous acceptance did not regress.

## Decision: Prioritize no-hang and CPU evidence before recording

**Rationale**: The prior implementation exposed hangs in Core Audio enumeration
and app bridge startup. These failures are easier to detect now and are
foundational for recording. Recording should not be built on top of a driver
that can hang macOS Sound settings, Zoom, Telemost, or browser settings.

**Alternatives considered**:

- Wait for recording before no-hang work: rejected because recording adds more
  complexity and would make root-cause analysis harder.
- Treat user observation only as sufficient: rejected because CPU and launch
  timing thresholds should be repeatable where possible.

## Decision: Keep evidence metadata-only

**Rationale**: This slice is pre-recording and must not create meeting-content
artifacts. Evidence should capture target app, selected devices, route state,
CPU observations, timing, pass/blocked state, and recovery action without raw
audio or transcript text.

**Alternatives considered**:

- Store temporary audio snippets for validation: rejected because it violates
  the pre-recording scope and would need retention/deletion policy.
- Use external observability: rejected because this slice must not add Langfuse,
  analytics, or network egress.

## Decision: Treat installer lifecycle as a release-hardening gate

**Rationale**: A virtual audio driver must be repeatedly installable,
repairable, updatable, removable, and recoverable without leaving Core Audio in
a confusing state. This is release-critical even before recording exists.

**Alternatives considered**:

- Delay installer lifecycle checks until packaging release: rejected because the
  driver is already installed during local testing, and broken cleanup causes
  downstream false failures.

## Decision: Preserve automatic non-recording passthrough startup

**Rationale**: Feature 004 user acceptance confirmed that requiring `Run Check`
for activation is not acceptable. Hardening should preserve automatic
non-recording startup while proving it does not hang common audio surfaces.

**Alternatives considered**:

- Revert to manual activation: rejected because it regresses accepted user
  behavior.
- Start recording automatically: rejected by constitution and out of scope.
