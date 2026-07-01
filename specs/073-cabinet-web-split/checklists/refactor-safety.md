# Refactor Safety Checklist: Cabinet Web Split

**Purpose**: Validate that 073 requirements are complete, clear, and safe before implementation.

**Created**: 2026-07-01

**Feature**: [spec.md](../spec.md)

## Scope And Lane

- [x] CHK-001 Is the risk lane explicitly significant architecture / high-risk behavior-preserving refactor? [Completeness]
- [x] CHK-002 Does the spec forbid behavior changes outside route organization? [Clarity]
- [x] CHK-003 Does the spec exclude templates, view models, egress, auth provider semantics, deletion service semantics, migrations, dependencies, infra, and deploy files? [Scope]
- [x] CHK-004 Is production deploy explicitly excluded? [Completeness]

## Route Contract Preservation

- [x] CHK-005 Are existing route paths, methods, response classes, redirect targets, and status behavior required to stay unchanged? [Completeness]
- [x] CHK-006 Is the stable public import `twobrain_rec_server.cabinet.web.router` required? [Clarity]
- [x] CHK-007 Are desktop embedded routes explicitly covered? [Completeness]
- [x] CHK-008 Are HX fragment routes explicitly covered? [Completeness]
- [x] CHK-009 Are browser auth, login, signup, provider, meeting, settings, calendar, and deletion routes covered? [Completeness]

## Security And Privacy

- [x] CHK-010 Are CSRF requirements preserved for existing POST routes? [Security]
- [x] CHK-011 Are authenticated principal, tenant scope, storage, and database dependencies required to stay intact? [Security]
- [x] CHK-012 Are no-secret content and deletion/retention truth covered? [Privacy]
- [x] CHK-013 Are route-policy and desktop WebView boundary changes excluded from this slice? [Boundary]

## Validation

- [x] CHK-014 Are focused cabinet tests named in the validation plan? [Measurability]
- [x] CHK-015 Is there a stop condition for behavior coupling larger than expected? [Recovery]
- [x] CHK-016 Does the quickstart explain when calendar-specific tests are required? [Coverage]
- [x] CHK-017 Are broader CI and deploy gates clearly separated? [Consistency]

## Ponytail Shape

- [x] CHK-018 Does the plan prefer existing helpers and tests over new scaffolding? [Consistency]
- [x] CHK-019 Does the plan forbid duplicating shared security-sensitive helpers? [Clarity]
- [x] CHK-020 Is the implementation goal a small split rather than a rewrite? [Clarity]
