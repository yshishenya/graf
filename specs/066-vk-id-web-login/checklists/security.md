# Security Checklist: VK ID Web Login

**Purpose**: Validate auth/security requirement quality before implementation
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

## Secret Boundary

- [x] CHK001 Are VK client secret custody requirements explicit and server-only? [Completeness, Spec §FR-010, FR-012]
- [x] CHK002 Does the spec prohibit rendering, logging, or committing raw VK secrets, OAuth codes, access tokens, and profile payloads? [Coverage, Spec §FR-012]
- [x] CHK003 Is missing or empty VK secret behavior specified as fail-closed? [Completeness, Spec §US3, Contract §Failure Behavior]

## Auth Flow Safety

- [x] CHK004 Are callback state mismatch, expiry, reuse, and missing-state cases specified? [Coverage, Spec §Edge Cases]
- [x] CHK005 Are unsafe browser return paths constrained to first-party cabinet paths? [Clarity, Spec §FR-005]
- [x] CHK006 Are disabled-provider and provider-unavailable failure modes specified without leaking provider internals? [Coverage, Spec §US2, FR-007]

## Scope Control

- [x] CHK007 Is the feature bounded to VK browser login without new provider families, migrations, or desktop token custody? [Clarity, Spec §FR-013]
- [x] CHK008 Are email fallback requirements preserved during provider failures? [Consistency, Spec §FR-011]
