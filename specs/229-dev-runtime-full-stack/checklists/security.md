# Security Requirements Checklist: Dev runtime

**Purpose**: Validate boundary, credential and non-mutation requirements

**Created**: 2026-09-01

**Feature**: [spec.md](../spec.md)

**Ownership**: Reviewer-owned; leave markers unchecked until security review.

- [ ] CHK001 Are production/staging environment, origin, path and credential rejection requirements complete? [Security, Spec §FR-004]
- [ ] CHK002 Are credentials prohibited from app bundles, logs, receipts and fixtures? [Secrets, Spec §FR-012]
- [ ] CHK003 Are loopback-only origins and host bindings unambiguous? [Boundary, Spec §FR-003, FR-004]
- [ ] CHK004 Is migration mismatch fail-closed before any API/worker readiness or data mutation? [Fail-closed, Spec §FR-005, FR-006]
- [ ] CHK005 Are `alembic stamp`, direct revision edits and destructive volume resets explicitly forbidden? [Data safety, Spec §FR-006]
- [ ] CHK006 Are app signing identity, designated requirement, bundle ID and updater metadata requirements complete? [Platform integrity, Spec §FR-007]
- [ ] CHK007 Is PID/container ownership verification required before stop or rollback signalling? [Process safety, Spec §FR-009]
- [ ] CHK008 Are external provider calls and their secret-custody boundary clearly separated from local readiness? [Egress, Spec §Assumptions, FR-012]
- [ ] CHK009 Are production app/data before-and-after fingerprints required for live evidence? [Non-mutation, Spec §SC-005]

## Notes

The checklist is a requirements gate; implementation agents must not mark items
complete.
