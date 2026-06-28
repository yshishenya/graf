# Security Checklist: Cabinet Login Polish

**Purpose**: Validate auth and secret-boundary requirements quality before implementation
**Created**: 2026-06-28
**Feature**: [spec.md](../spec.md)

## Auth Boundary Requirements

- [x] CHK001 Does the spec define when external OAuth provider origins may be embedded and keep unknown origins outside auth continuation blocked? [Completeness, Spec FR-001, FR-002]
- [x] CHK002 Does the spec require desktop headers to stay off provider-origin requests? [Completeness, Spec FR-002]
- [x] CHK003 Does the spec avoid changing provider callback verification or desktop token access? [Consistency, Spec FR-009]

## Secret And Evidence Requirements

- [x] CHK004 Does the spec prohibit raw OAuth codes, tokens, secrets, and private identifiers in rendered HTML, logs, specs, tests, and evidence? [Completeness, Spec FR-009]
- [x] CHK005 Does quickstart validation avoid requiring real credentials or captured live tokens? [Coverage, quickstart.md]

## Failure Handling

- [x] CHK006 Are unsupported providers and unknown external URLs required to remain fail-closed? [Coverage, Edge Cases]
