# Phase 0 Research: Live Route Stability

## Decision: Preserve Active Meeting Routes From Client Activity Evidence

**Decision**: Treat virtual-device client activity and freshness windows as the
authority for preserving an active meeting route. Audio energy and natural
silence are never sufficient reasons to release a route.

**Rationale**: The incident pattern maps to the current idle policy: the route
can be released after `300` idle ticks when `anyExpectedVirtualDeviceRunning()`
returns false. A long meeting has many valid quiet periods, browser stream
recreations, and one-sided activity windows. The product requirement is that
active meeting routes stay alive unless fresh evidence proves the meeting target
stopped using both virtual devices.

**Alternatives considered**:

- Keep the existing `300` tick idle release: rejected because the observed
  bridge stops were around 300 seconds and required `Run Check`.
- Use audio level/energy to infer meeting activity: rejected because local or
  remote silence is a valid meeting state.
- Disable all release forever: rejected because explicit user/device closure
  still needs bounded resource release and truthful state.

## Decision: Idle Release Is Deny-By-Default For Ambiguous Active Routes

**Decision**: A route release decision requires fresh, positive evidence that
the meeting client closed the virtual route. If evidence is stale, partial, or
ambiguous, preserve the route and emit a metadata-only release-denied event.

**Rationale**: The feature is a prevention-first stability gate. A false release
is worse than preserving the route during ambiguity because false release breaks
the meeting and recording timeline.

**Alternatives considered**:

- Release on unknown state to save resources: rejected because it recreates the
  "works only after Run Check" failure.
- Convert unknown to stale and wait for manual recheck: rejected because user
  action is not the accepted recovery path.

## Decision: Follow macOS System Default Routes Via Core Audio Properties

**Decision**: 2brain Rec follows macOS default physical input/output. It should
observe default route changes with Core Audio property listeners and use polling
as a fallback/safety net outside realtime callbacks.

**Rationale**: The spec clarified that the user selects 2brain Rec virtual
devices inside the meeting app, while physical input/output follows macOS
system defaults. Apple documents the current default input device through
`kAudioHardwarePropertyDefaultInputDevice` in TN2091, and Core Audio exposes
property listener blocks for property-change notification. Apple also notes
that some device-running notifications can be dispatched from the IO context,
so route-change handling must hand off to a safe app queue rather than do
repair work in realtime context.

**Primary sources**:

- Apple Technical Note TN2091, "Device input using the HAL Output Audio Unit":
  https://developer.apple.com/library/archive/technotes/tn2091/_index.html
- Apple Developer Documentation, `AudioObjectAddPropertyListenerBlock`:
  https://developer.apple.com/documentation/coreaudio/audioobjectaddpropertylistenerblock%28_%3A_%3A_%3A_%3A%29
- Apple Developer Documentation, `AudioObjectPropertyListenerBlock`:
  https://developer.apple.com/documentation/coreaudio/audioobjectpropertylistenerblock
- Apple Developer Documentation, `kAudioDevicePropertyDeviceIsRunning`:
  https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertydeviceisrunning

**Alternatives considered**:

- Add a 2brain Rec physical-device picker: rejected for `019`; it conflicts with
  the clarified macOS-default model and creates privacy/device-ownership risk.
- Keep selected physical device ids from previous setup as persistent truth:
  rejected because macOS default can change during a meeting and must be
  followed for accepted built-in/wired/USB routes.
- Rely only on polling: acceptable as fallback, rejected as sole strategy
  because route change latency matters for the `<= 2s`/`<= 10s` repair gates.

## Decision: Autorepair Is A Bounded State Machine

**Decision**: Autorepair uses explicit states: `observed`, `classifying`,
`repairing`, `awaiting_os_condition`, `healthy_after_fresh_evidence`,
`degraded`, `blocked_non_recoverable`, `failed`, and
`retry_budget_exhausted`.

**Rationale**: The current code marks `coreaudiod` restart as stale and logs
"requires recheck". The product requirement is automatic repair for supported
recoverable disruptions and truthful blocking for non-recoverable states.
State-machine boundaries prevent infinite churn and prevent reporting healthy
before fresh route evidence exists.

**Alternatives considered**:

- Direct restart on every stale signal: rejected because it can churn a healthy
  route and hide root cause.
- Manual `Run Check` as primary recovery: rejected by spec.
- Treat all failures as recoverable: rejected because missing permissions,
  missing devices, unsupported Bluetooth/AirPods defaults, and meeting target
  device changes are non-recoverable for `019`.

## Decision: Keep Repair Work Off Realtime Audio Paths

**Decision**: Core Audio/HAL callbacks may only update realtime-safe counters or
shared memory facts already permitted by existing code. Classification,
logging, file IO, device enumeration, route rebuild, and manifest writes happen
on app queues or validation scripts.

**Rationale**: The constitution and spec prohibit file IO, logging, allocation,
locks, network calls, process launches, UI work, or unbounded waits in
realtime callbacks. Apple Core Audio listener documentation also requires care
because some notifications can be delivered from IO context.

**Alternatives considered**:

- Emit rich logs directly from render/input callbacks: rejected as realtime
  unsafe.
- Do route repair directly from a property listener callback: rejected unless it
  only dispatches to a non-realtime queue.

## Decision: Evidence Is Metadata-Only And Local-First

**Decision**: Route evidence is structured metadata with redaction gates:
event family, route/session ids, meeting target label, safe device ids/names,
device class, trigger, state before/after, frame continuity summary, attempt
count, elapsed time, user-action-required boolean, and recording alignment band.

**Rationale**: Debugging needs to reconstruct why a route released or repaired,
but diagnostics must not contain raw audio, transcript text, meeting content,
credentials, tokens, signed URLs, passwords, or live credential paths.

**Alternatives considered**:

- Store short debug audio clips: rejected for `019`; belongs to a separate
  privacy-reviewed diagnostic feature if ever needed.
- Use unstructured `/tmp/2brain-rec-bridge.log` text as final evidence:
  rejected because it is not enough for long-duration acceptance, redaction, or
  target/device matrix claims.

## Decision: Recording Timeline Evidence Extends Manifest Truth

**Decision**: Add route-stability categories to local recording manifest
evidence: route session id, route gap windows, interruption category,
autorepair correlation, track durations, duration difference seconds, alignment
band, and whether the run counts as clean acceptance.

**Rationale**: The 2026-06-04 artifact had a generic `timeline_misaligned`
failure and an incoming track about 152 seconds shorter than the mic track. The
new feature must distinguish route interruption from other manifest failures.

**Alternatives considered**:

- Only compare final durations: insufficient because it does not explain cause.
- Treat live audibility as enough: rejected because the saved artifact can still
  be degraded.

## Decision: Validation Separates Target Coverage From Device-Class Coverage

**Decision**: Release evidence must show accepted long-duration runs for Chrome,
Opera, Zoom, and Telemost, and accepted long-duration runs for built-in, wired,
and USB device classes. The full `4 x 3` cross-product is not required unless a
future hardening gate adds it.

**Rationale**: This matches the clarified acceptance scope and avoids claiming
untested combinations as release-ready.

**Alternatives considered**:

- Full cross-product now: rejected as too broad for the `019` slice and not
  required by the clarified spec.
- Single happy-path target/device run: rejected because every target and every
  in-scope class must have long-duration evidence.

## Decision: Bluetooth/AirPods Are Deferred With Explicit Evidence

**Decision**: If the macOS default route resolves to Bluetooth/AirPods-class
during an active `019` run, log it as deferred/not accepted and block clean
acceptance for that run.

**Rationale**: Wireless headset profile switching, latency, reconnect behavior,
and bidirectional route churn are a different risk class and were explicitly
deferred to backlog.

**Alternatives considered**:

- Treat Bluetooth as unknown physical: rejected because it could silently imply
  support.
- Fail hard without evidence: rejected because backlog/debug evidence is useful.
