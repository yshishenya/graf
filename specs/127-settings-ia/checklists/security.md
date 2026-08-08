# Security Requirements Quality Checklist: единая архитектура настроек

**Purpose**: Validate that authentication, tenant, secret and privacy
requirements are explicit before implementation.
**Created**: 2026-07-25
**Feature**: [spec.md](../spec.md)
**Audience**: Security and implementation reviewer.

## Authentication and authorization

- [x] CHK001 — Are all protected settings assumed to use the current authenticated session and active workspace? [Coverage, Spec §FR-017, Data model]
- [x] CHK002 — Are owner-only summary defaults and workspace/device permissions explicitly distinguished from ordinary member access? [Clarity, Spec §FR-004, FR-006, FR-009]
- [x] CHK003 — Is the device revoke action required to preserve the existing authorization and audit boundary? [Traceability, Spec §FR-009, research Decision 4]
- [x] CHK004 — Are fixed return targets required instead of arbitrary redirect URLs? [Abuse prevention, Contract §Canonical routes]

## Secret and privacy boundaries

- [x] CHK005 — Does the specification explicitly forbid provider subjects, candidate contacts, credentials, tokens, raw audio and meeting content in rendered settings? [Completeness, Spec §Edge Cases, SC-007]
- [x] CHK006 — Is calendar credential custody kept server-side and separated from native desktop settings? [Consistency, Spec §FR-007, FR-017]
- [x] CHK007 — Are direct provider-link and calendar failure states required to avoid echoing submitted secrets? [Exception coverage, Spec §Edge Cases, SC-005, SC-007]
- [x] CHK008 — Are privacy-preserving labels defined for account providers and devices rather than raw identifiers? [Clarity, research Decision 4, Data model]

## Tenant isolation and lifecycle

- [x] CHK009 — Are current-user and current-workspace filters required for account, workspace and calendar projections? [Tenant boundary, Data model]
- [x] CHK010 — Does the feature explicitly avoid new deletion promises or changes to observability retention? [Scope, Spec §Out of Scope, Constitution §IV]
- [x] CHK011 — Are CSRF requirements retained for every settings mutation, including workspace, provider-link, calendar and device actions? [Completeness, Spec §FR-017, Contract §Mutation states]
- [x] CHK012 — Are admin operations explicitly kept outside personal/workspace settings navigation? [Separation of privilege, Spec §FR-010]
