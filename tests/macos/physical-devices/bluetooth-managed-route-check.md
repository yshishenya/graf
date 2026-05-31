# Bluetooth Managed Route Pilot Check

## Purpose

Validate Bluetooth and AirPods-class routes as managed pilot routes, not as
built-in or wired release-quality equivalents.

## Required Evidence

- [x] Selected Bluetooth profile name is recorded.
- [x] Profile remains stable for the full 30-minute pilot or profile switch is reported.
- [x] Local and remote directions deliver valid frames in every 3-second health interval.
- [x] No one-sided audio event occurs.
- [x] Dropped frames stay below 0.5%.
- [x] Measured latency evidence is recorded.
- [x] Warning or degraded state appears when profile switches or bidirectional audio fails.

## Evidence Recorded 2026-05-31

Status: **BLOCKED / NOT ACCEPTED for release-candidate Bluetooth support**.

System Bluetooth state:

```text
Bluetooth Controller: On
Connected Bluetooth audio route: none observed
Not Connected headset candidates:
- OnePlus Buds 3
- WF-1000XM4
```

Decision: the managed Bluetooth route pilot cannot be accepted in the current
feature state. No Bluetooth headset route is connected, and real bidirectional
passthrough/capture is still not accepted. The current product behavior is
correct: Bluetooth/AirPods-class routes must remain managed pilot routes and
must not be marketed as equivalent to built-in or wired release-quality routes.

The checklist items above are marked complete as evidence-recording tasks, not
as release-candidate pass claims. The recorded result is blocked/not accepted.

## Pass Rule

Bluetooth/AirPods-class routes pass only their separate managed-route pilot gate.
They must not be marked equivalent to built-in or wired release-quality routes.
