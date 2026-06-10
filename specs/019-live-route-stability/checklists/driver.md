# Driver Checklist: Live Route Stability

**Purpose**: Validate driver and route-engine requirement quality before task generation.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and planning artifacts, not implementation behavior.

## Route Preservation

- [x] CHK001 Are requirements complete for preserving active routes when only mic-side, only speaker-side, or both-side virtual client evidence is fresh? [Completeness, Spec §FR-004, Spec §FR-005, Data Model §ClientActivitySnapshot]
- [x] CHK002 Are requirements clear that natural silence and audio energy cannot be used as sufficient release evidence? [Clarity, Spec §FR-004, Research §Preserve Active Meeting Routes]
- [x] CHK003 Are idle-release requirements precise enough to require fresh proof that the meeting client closed the virtual route before release? [Measurability, Spec §FR-022, Spec §FR-023, Data Model §RouteReleaseDecision]
- [x] CHK004 Are ambiguous/stale activity requirements consistent with preserving the route instead of releasing it? [Consistency, Research §Idle Release, Plan §Phase 1]
- [x] CHK005 Are app restart, `coreaudiod`, sleep/wake, browser stream recreation, and transient client I/O changes represented as route states rather than generic failures? [Coverage, Spec §FR-008, Data Model §LiveRouteState]

## macOS Default Route Model

- [x] CHK006 Are macOS system default input/output requirements complete enough to avoid a 2brain Rec physical-device picker in `019`? [Completeness, Spec §FR-026, Spec §FR-027]
- [x] CHK007 Are requirements clear that accepted default-route following applies only to built-in, wired, and USB classes? [Clarity, Spec §FR-049, Data Model §PhysicalDeviceClass]
- [x] CHK008 Are unsupported default-route classes, including Bluetooth/AirPods, defined as deferred/not accepted rather than hidden failures? [Consistency, Spec §FR-042, Spec §SC-020, Research §Bluetooth/AirPods]
- [x] CHK009 Are Core Audio property-listener and polling-fallback requirements documented with enough boundaries for non-realtime route monitoring? [Coverage, Research §macOS System Default Routes]

## Realtime Safety

- [x] CHK010 Are realtime-safety requirements complete for Core Audio/HAL callbacks and all route-monitoring handoffs? [Completeness, Spec §FR-018, Research §Realtime Audio Paths]
- [x] CHK011 Are requirements explicit that logging, file IO, route rebuild, device enumeration, UI work, and process launch remain outside realtime callbacks? [Clarity, Spec §FR-018]
- [x] CHK012 Are repair-dispatch requirements consistent with Apple listener caveats and the project realtime-safety gate? [Consistency, Research §Realtime Audio Paths, Constitution §I]

## State And Contract Readiness

- [x] CHK013 Are driver-facing route states mapped clearly enough to shared model states and evidence contracts? [Traceability, Data Model §LiveRouteState, Contract §Route Evidence Events]
- [x] CHK014 Are startup, active, preserved, stale, recovering, blocked, failed, released, and stopped states distinct enough for future task boundaries? [Clarity, Data Model §LiveRouteState]
- [x] CHK015 Are driver route requirements scoped to live stability without drifting into `020` leakage/echo cleanup? [Scope, Spec §Scope Boundary, Plan §Constraints]
