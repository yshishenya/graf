# Security Requirements Checklist: Remove Workspace Legacy

**Purpose**: Validate auth, tenant, billing and cleanup requirements before implementation
**Created**: 2026-08-15
**Feature**: [spec.md](../spec.md)

## Trust Boundary Completeness

- [x] CHK001 Is the internal auth anchor explicitly excluded from customer membership, session, device, meeting, upload and billing scopes? [Completeness, Spec §FR-003–FR-004]
- [x] CHK002 Is direct activation/session continuation for the internal anchor specified as fail closed even with stale membership? [Clarity, Spec §FR-006]
- [x] CHK003 Are personal repair and ambiguous-recovery outcomes distinguished? [Coverage, Spec §FR-007]
- [x] CHK004 Is explicit identity-verified enrollment required before corporate membership? [Completeness, Spec §FR-005]
- [x] CHK005 Is first corporate-owner provisioning separated from public signup/login? [Boundary, Spec §FR-005]
- [x] CHK006 Are personal/internal invitation and offer targets forbidden? [Coverage, Spec §FR-015]

## Billing And Data Isolation

- [x] CHK007 Is self-serve billing limited to an active personal owner for every named mutation class? [Clarity, Spec §FR-010]
- [x] CHK008 Is the internal anchor forbidden as a meetings/uploads/devices/usage/billing subject? [Consistency, Spec §FR-004, FR-010]
- [x] CHK009 Are revoked corporate access and personal ownership kept independent without silent work retargeting? [Coverage, Spec §Edge Cases, FR-007]

## Cleanup And Evidence

- [x] CHK010 Does cleanup stop on any customer or financial row instead of moving/deleting it? [Safety, Spec §FR-012]
- [x] CHK011 Are backup, zero-data inventory and separate production approval explicit prerequisites? [Completeness, Spec §FR-012, Assumptions]
- [x] CHK012 Is one-shot cleanup evidence distinguished from the removed permanent legacy CLI? [Consistency, Spec §FR-011–FR-012]
- [x] CHK013 Are evidence and audit requirements metadata-only with prohibited secrets/content named? [Privacy, Spec §FR-013]

## Scope Control

- [x] CHK014 Are unrelated header-auth, media/audio and macOS migration compatibility contracts explicitly out of scope? [Boundary, Spec §FR-014, Assumptions]
- [x] CHK015 Can every negative bootstrap scenario be objectively verified through the success criteria? [Measurability, Spec §SC-002–SC-006]

## Notes

- All security requirement-quality items pass; implementation evidence is tracked in quickstart/tasks.
