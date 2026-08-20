# Security Requirements Checklist: Надёжный вход по email

**Purpose**: Validate auth, transaction, RLS and privacy requirements before implementation
**Created**: 2026-08-19

## Requirement Completeness

- [x] CHK001 Are exact callback, session, identity and merge rollback boundaries specified? [Completeness, Spec §FR-001–FR-007]
- [x] CHK002 Are successful, invalid, expired, replayed and concurrent code outcomes covered without arbitrary session issuance? [Coverage, Spec §US1, Edge Cases]
- [x] CHK003 Are RLS contexts bounded without maintenance-role or policy widening? [Security, Spec §FR-002–FR-003]
- [x] CHK004 Is route ownership of the single commit and pre-commit response preparation explicit? [Clarity, Spec §FR-005]
- [x] CHK005 Are audit writes and callback terminal writes assigned to separately authorized contexts? [Security, Spec §FR-007]

## Account Recovery And Merge Safety

- [x] CHK006 Does the spec prohibit account selection from normalized email equality alone? [Security, Spec §FR-008, FR-015]
- [x] CHK007 Is the 0/1/>1 other-user matrix defined after excluding the current user? [Clarity, Spec §FR-011–FR-015]
- [x] CHK008 Is automatic cross-account confirmation prohibited even for zero bounded data counts? [Safety, Spec §FR-014]
- [x] CHK009 Are merge intent, preview, explicit confirmation, cancellation, replay and blocker semantics covered? [Coverage, Spec §US3]
- [x] CHK010 Is the OAuth provider-link sibling context leak included rather than left as an unrelated follow-up? [Completeness, Spec §FR-017]

## Trust Boundaries And Evidence

- [x] CHK011 Are CSRF, OAuth state/nonce, rate-limit, verified-email and safe-destination protections preserved? [Security, Spec §FR-010]
- [x] CHK012 Are web and embedded routes constrained to their existing first-party boundaries? [Security, Spec §FR-018]
- [x] CHK013 Are logs, audit and committed evidence explicitly metadata-only and free of real identifiers? [Privacy, Spec §FR-020]
- [x] CHK014 Is real production merge/repair excluded from implementation validation? [Boundary, Spec §Out of Scope]
- [x] CHK015 Is a non-owner forced-RLS regression required in addition to owner-role HTTP tests? [Measurability, Spec §SC-001–SC-003]

## Notes

- Review audience: PR author, independent auth reviewer and release gate.
- All requirements-quality items pass after the 2026-08-19 clarification/research pass.
