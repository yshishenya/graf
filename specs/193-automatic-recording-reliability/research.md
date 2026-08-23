# Research: Automatic Recording Reliability

## Decision 1: Independent source ownership

**Decision**: every `MacOSAudioOwnershipEvent` carries `audioHAL` or
`sensorIndicator`; the detector stores an active source set for each bundle and
starts end grace only when that set is empty.

**Rationale**: AudioHAL assertion lifecycle and Control Center attribution are
independent observations. Collapsing them into one Boolean makes the result
depend on event order and lets one inactive event cancel the other active source.

**Rejected**: source precedence or a time-only heuristic. Neither can distinguish
an ended assertion from a still-active independent microphone attribution.

## Decision 2: Consumer acknowledgement, not emission, closes a trigger

**Decision**: the detector keeps a stable candidate eligible until its prompt or
start trigger is accepted by the app consumer, or until a terminal user action
(Skip/manual Stop) or real end boundary occurs. Retryable rejection is evaluated
again no more frequently than once per 2 seconds.

**Rationale**: the detector currently marks prompt, auto-start and suppressions
as emitted before the consumer can reject them. A temporary transition, active
prompt, auth refresh or readiness blocker therefore swallows the only trigger.

**Rejected**: retrying every advance tick (log spam and start races) or clearing
all state after rejection (duplicate countdowns and terminal-action violations).

## Decision 3: One gate before any countdown promise

**Decision**: `meetingDetectionPrerequisites()` includes current assisted
authorization. Both prompt/countdown and saved-target trigger use it; every actual
start still calls `currentMeetingDetectionStartDecision()` immediately before
capture.

**Rationale**: current UI can promise a timeout start while passing
`requiresAssistedAuthorization: false`, then silently fail at timeout when the
same authorization is finally required.

**Rejected**: allowing countdown while disabled and explaining only at timeout.
That knowingly presents a false recording promise.

## Decision 4: Supervised observer with bounded snapshot

**Decision**: one async supervisor owns `/usr/bin/log`. Each iteration first runs
a Control Center sensor-attribution `log show --last 2h` snapshot with a hard
3.5-second deadline, publishes only its final complete attribution set
atomically, then opens the ordinary AudioHAL plus sensor `log stream`. An
unavailable/slow snapshot fails closed and proceeds to live observation;
unexpected live completion retries after one second. Deliberate stop cancels the
supervisor and child. Wake terminates the current child so the supervisor resets
detector state, reconciles a fresh bounded snapshot and opens one new stream.

**Rationale**: completed `AsyncStream` currently leaves a non-nil task and wake
cannot restart it. Live stream also has no initial state, so launching during an
active call misses the candidate. Runtime verification showed that replaying the
combined one-day AudioHAL/sensor history took 54 seconds and exposed historical
intermediate states to decisioning. The bounded sensor snapshot completes within
the five-second recovery budget on the tested runtime, while atomic final-state
publication cannot trigger from an earlier stale transition.

**Rejected**: the combined one-day AudioHAL history (unbounded runtime and stale
intermediate candidates), periodic full log polling (more work and duplicate
events), parallel snapshot/live processes (ordering race), or
Accessibility/window heuristics (new privacy boundary and unverified eligibility).

## Decision 5: Reset detector state at observation boundaries

**Decision**: clear tracked source/candidate state before reconciling each fresh
snapshot after startup, restart or wake. A continuous live stream retains state.

**Rationale**: after lost end events, stale active sources otherwise block future
meetings indefinitely. Snapshot rebuild is the only trustworthy current boundary
available without adding a new platform monitor.

## Decision 6: Authoritative WebKit cookie snapshot

**Decision**: for the configured same-origin auth cookie, WebKit presence replaces
all applicable native copies and WebKit absence removes them. Native selection
filters applicability and then orders deterministically by non-expired state,
HTTPS compatibility, domain/path specificity and expiry.

**Rationale**: append-only sync leaves stale native sessions after replacement or
logout, while selecting the first same-name cookie depends on storage order.

**Rejected**: clearing the entire native cookie store (breaks unrelated origins)
or forwarding a general `Cookie` header (widens credential egress).

## Decision 7: Existing metadata logger

**Decision**: reuse `AppLog.writeRaw` for bounded source transition, detector
decision, consumer outcome and observer lifecycle events. Never log process line,
cookie value, meeting title/content or filesystem secret path.

**Rationale**: a new telemetry subsystem is unnecessary; the missing value is a
complete safe event chain, not a new storage backend.

## Decision 8: Server and rollout boundary

**Decision**: do not change server schemas/config or production values. Existing
fail-closed policy behavior is correct; current production policy being disabled
is a deployment/configuration fact, not a reason to weaken client authorization.

**Rationale**: client reliability can be fixed and fully tested locally. Enabling
policy, deploying, replacing `/Applications/GRAF.app`, signing and releasing need
separate exact-runtime approval and evidence.
