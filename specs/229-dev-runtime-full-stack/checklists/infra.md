# Infrastructure Requirements Checklist: Dev runtime

**Purpose**: Validate infrastructure requirements before implementation

**Created**: 2026-09-01

**Feature**: [spec.md](../spec.md)

**Ownership**: Reviewer-owned; leave markers unchecked until evidence is reviewed.

- [x] CHK001 Are all Compose services, dependencies and readiness conditions named? [Completeness, Spec §FR-001]
- [x] CHK002 Are Compose project, volume, network, port and state-root isolation rules measurable? [Clarity, Spec §FR-003]
- [x] CHK003 Is migration preflight ordered before API and worker readiness? [Ordering, Spec §FR-005]
- [x] CHK004 Are empty, matching, unknown, divergent and multiple-head migration states covered? [Coverage, Spec §Edge Cases]
- [x] CHK005 Are bounded startup, health-check and process-stop timeouts defined? [Reliability, Spec §Performance Goals]
- [x] CHK006 Are Temporal, processing-worker and media-worker readiness requirements independently named? [Traceability, Spec §FR-011]
- [x] CHK007 Is rollback behavior defined when a Compose service, app install or smoke check fails? [Recovery, Spec §FR-009, FR-010]
- [x] CHK008 Are old local volumes and production services explicitly excluded from every lifecycle operation? [Boundary, Spec §FR-004, FR-006]
- [x] CHK009 Is the clean-state live smoke evidence scope defined without private content? [Evidence, Spec §SC-007]

## Notes

The checklist validates requirement quality, not implementation behavior.
