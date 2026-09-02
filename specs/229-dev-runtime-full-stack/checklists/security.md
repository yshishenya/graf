# Security Requirements Checklist: Dev runtime

**Purpose**: Validate boundary, credential and non-mutation requirements

**Created**: 2026-09-01

**Feature**: [spec.md](../spec.md)

**Ownership**: Reviewer-owned; leave markers unchecked until security review.

- [X] CHK001 Are production/staging environment, origin, path and credential rejection requirements complete? [Security, Spec §FR-004]
- [X] CHK002 Are credentials prohibited from app bundles, logs, receipts and fixtures? [Secrets, Spec §FR-012]
- [X] CHK003 Are loopback-only origins and host bindings unambiguous? [Boundary, Spec §FR-003, FR-004]
- [X] CHK004 Is migration mismatch fail-closed before any API/worker readiness or data mutation? [Fail-closed, Spec §FR-005, FR-006]
- [X] CHK005 Are `alembic stamp`, direct revision edits and destructive volume resets explicitly forbidden? [Data safety, Spec §FR-006]
- [X] CHK006 Are app signing identity, designated requirement, bundle ID and updater metadata requirements complete? [Platform integrity, Spec §FR-007]
- [X] CHK007 Is PID/container ownership verification required before stop or rollback signalling? [Process safety, Spec §FR-009]
- [X] CHK008 Are external provider calls and their secret-custody boundary clearly separated from local readiness? [Egress, Spec §Assumptions, FR-012]
- [X] CHK009 Are production app/data before-and-after fingerprints required for live evidence? [Non-mutation, Spec §SC-005]

## Notes

The checklist is a requirements gate; implementation agents must not mark items
complete.

Reviewed by Codex `code-reviewer` on 2026-09-02; this approves requirement
quality only and does not substitute for implementation or live evidence.
