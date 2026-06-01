# Checklist: Live Passthrough Requirement Quality

**Purpose**: Validate that live audio route requirements are complete and
release-testable before implementation.

- [x] CHK001 Does the spec clearly distinguish virtual-device visibility from call readiness?
- [x] CHK002 Are microphone and speaker path success conditions measurable without relying on raw audio storage?
- [x] CHK003 Is self-routing rejection required for both physical input and output selection?
- [x] CHK004 Is remote-to-microphone loopback explicitly forbidden and thresholded?
- [x] CHK005 Is readiness invalidation required after physical device, browser target, or route changes?
- [x] CHK006 Are backend/network failures separated from local passthrough failures?
- [x] CHK007 Are Bluetooth and AirPods-class profile changes represented as failure/recovery cases?
- [x] CHK008 Does the release gate require real browser meeting evidence, not only synthetic checks?
- [x] CHK009 Does the spec distinguish ordinary user silence from missing valid audio frames?
- [x] CHK010 Are 3-second hard stream-health failures and 30-second non-critical quality warnings represented separately?
- [x] CHK011 Is Krisp-like private app I/O fail-closed behavior represented without copying closed implementation?

## Notes

Requirements are ready for tasks. Implementation must keep the clean-room
Krisp-like behavior: private app I/O, AEC/reference separation, fast
capturability failure, and no degraded state for ordinary silence with valid
frames.
