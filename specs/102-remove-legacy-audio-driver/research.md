# Research: Remove Legacy Separate Audio Driver

## Decision 1: Protect the current recording graph as the fixed boundary

**Decision**: Preserve the current app-owned graph without redesign:
`ScreenCaptureKitSystemAudioCaptureRuntime` feeds a
`BufferedLocalRecordingSampleSource`; `MicrophoneCaptureService` supplies the
app-owned microphone source; `LocalRecordingWriter` writes the two original
tracks and manifest. Live meters read `LiveRecordingLevels` from the writer.

**Rationale**: This path is already independent of the HAL driver and is the
accepted product architecture. Before modifications, 62 focused tests covering
the graph, package, gate, and capture safety passed with zero failures.

**Alternatives rejected**:

- Rewrite recording while deleting the driver: unnecessary risk and out of
  scope.
- Keep shared memory as a dormant fallback: preserves a hidden dependency and
  lets the obsolete architecture re-enter production.

## Decision 2: Delete executable legacy clusters, adapt only mixed files

**Decision**: Delete the HAL source/build tree, C shared-memory helper, Swift
shared-memory wrapper, passthrough bridge/engine/coordinator/monitor, live-route
and low-resource routing clusters, route evidence store, driver/route setup UI,
driver-only health/installer services, and their tests. Adapt `Package.swift`,
`TwoBrainRecApp.swift`, current writer/gate/evidence/models, diagnostics, and
installer scripts because they also contain supported behavior.

**Rationale**: Dependency classification shows those deleted clusters converge
on the obsolete virtual-device route. The mixed files contain the supported
system-audio graph and cannot be removed wholesale.

**Alternatives rejected**:

- Leave dead types for source compatibility: there is no supported external
  library contract, and dead models keep the second architecture maintainable.
- Rename the old route engine: changing names would not remove behavior.

## Decision 3: Remove shared-memory defaults from the writer

**Decision**: Delete `SharedMemoryRecordingSampleSource`,
`sharedMemoryFactory`, and the implicit incoming-source fallback. The writer's
incoming source is explicitly injected by `SystemAudioCaptureService` in the
product app. Tests may inject buffered fakes.

**Rationale**: The product composition root already injects both current sample
sources. An implicit driver fallback makes a default-constructed writer open the
obsolete bridge even though normal recording does not need it.

**Alternatives rejected**:

- Return a no-op shared-memory adapter: adds an abstraction solely to preserve
  removed code.
- Keep the factory for old tests: tests must express the supported input source
  explicitly.

## Decision 4: Simplify recording eligibility and evidence

**Decision**: Remove `LivePassthroughStatus` and
`RecordingRouteEvidenceKind` from `RecordingPrerequisiteSnapshot`; replace the
single misleading microphone-only flag with current combined capture-permission
truth. Replace the route state in `RecordingEvidenceEvent` with the current
`CaptureSessionState`. Eligibility continues to check source policy, current
capture permission truth, storage, visible indicator, and source eligibility.
Remove obsolete route blockers and stop reasons.

**Rationale**: The current path always manufactured
`.systemAudioCapture` specifically to bypass the legacy route branch. The fields
are ephemeral diagnostics/meeting-detection inputs, not required fields in the
current recording manifest. Older JSON containing removed keys remains
decodable because unknown keys are ignored.

**Alternatives rejected**:

- Hard-code a permanently active route state: preserves misleading semantics.
- Make driver route fields optional: keeps dead branching and maintenance.

## Decision 5: Retain only generic microphone-device safety

**Decision**: Replace the driver-oriented self-routing classifier with a small
current recording microphone policy that accepts proven physical/Bluetooth
inputs and rejects virtual, aggregate, multi-output, unavailable, or unknown
inputs. Remove product-specific virtual device names/UIDs and the
`twoBrainVirtual` classification.

**Rationale**: Current recording must not capture from an unproven virtual
input, including a stale proof component, but the rule does not need to know the
removed driver's identity.

**Alternatives rejected**:

- Delete input classification entirely: could silently select an unsupported
  virtual source and break recording truth.
- Keep GRAF driver identifiers in runtime code: violates the retirement
  boundary and is unnecessary when unknown inputs already fail closed.

## Decision 6: Keep generic leakage metadata, remove route-lifecycle evidence

**Decision**: Keep `RecordingRouteMetadata` fields that describe physical
input/output class, mute/volume, route changes, sleep/wake, and leakage context.
Delete `RecordingTimelineIntegrityEvidence`, live-route session/autorepair
identifiers, and route evidence events that were generated only by the old
engine.

**Rationale**: Leakage analysis still needs physical acoustic context and is
not the separate driver. Route lifecycle identifiers have no current producer;
the manifest field is optional and can be removed without rewriting historical
files.

**Alternatives rejected**:

- Delete every symbol containing “route”: would remove supported physical audio
  and leakage truth.
- Preserve old timeline structs as historical code: historical specs and
  fixtures are the appropriate audit surface.

## Decision 7: Make packaging app-only

**Decision**: Adapt `build-local-installer.sh` to build one desktop app
component and one distribution choice. Delete driver `postinstall`, `repair`,
and `rollback` scripts. Adapt the ordinary uninstall script to remove only the
app; it must not contain HAL cleanup or restart audio services.

**Rationale**: Optional driver packaging is still a shippable path. Normal app
uninstall must not perform unrequested privileged cleanup of legacy proof state.

**Alternatives rejected**:

- Keep `GRAF_INCLUDE_DRIVER_COMPONENT=0`: the toggle can be re-enabled and keeps
  all driver packaging live.
- Automatically remove stale HAL bundles during install/update: hidden host
  mutation and unsafe during normal rollout.

## Decision 8: Document installed proof cleanup, do not automate it

**Decision**: Add bounded operator guidance that first inspects the exact known
bundle path and identifier, then removes only that component with explicit
administrator action. Do not ship a cleanup executable or invoke `killall
coreaudiod` from build/tests/app installer.

**Rationale**: Git source state and host installation state are separate.
Automatic cleanup would broaden this feature into a privileged migration and
could disrupt live audio.

**Alternatives rejected**:

- Ignore installed proof state: leaves operators with a misleading “removed”
  claim.
- Add a normal-build cleanup hook: violates least surprise and SC-009.

## Decision 9: Preserve audit history, reconcile active truth

**Decision**: Keep historical Spec Kit slices and failure evidence. Update the
root guide, current status, PRD, macOS README, ADR chain, changelog, and active
finding to say the implementation is removed. Future advanced routing requires
a new approved design and cannot revive this code.

**Rationale**: Historical evidence explains the pivot and supports future
security review. Active sources must not describe a parked implementation as
available.

**Alternatives rejected**:

- Delete all historical specs: destroys decision and incident evidence.
- Leave active docs unchanged: future maintainers would receive contradictory
  architecture instructions.

## Decision 10: Use a read-only negative architecture guard

**Decision**: Delete the active `SystemAudioNoHALEvidence` model and replace
driver runtime validators with one shell guard that scans
active source/build/installer/test/documentation roots for exact retired symbols
and payloads. Historical specs/ADR/evidence and the guard's own pattern list are
the only explicit allowlist. The guard writes nothing and performs no service
mutation.

**Rationale**: A small absence assertion protects the architectural decision
without maintaining deleted runtime behavior.

**Alternatives rejected**:

- Keep the existing no-HAL proof script unchanged: it writes into historical
  evidence and still models a parked driver.
- Rely on reviewer memory: the optional installer path and implicit writer
  fallback already demonstrate why a machine-enforced boundary is useful.
