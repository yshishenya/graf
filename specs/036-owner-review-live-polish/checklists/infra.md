# Infra Requirements Quality Checklist: Owner Review Live Polish

**Purpose**: Validate live production proof, smoke-session, deployment, and operational evidence requirements
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is the production target origin explicitly defined as `https://rec.2brain.pro`? [Completeness, Data Model §OwnerReviewProof]
- [x] CHK002 Are dry-run and execute-mode smoke-session paths documented separately? [Completeness, Quickstart §3/§4]
- [x] CHK003 Are cleanup and local token-file deletion requirements included in validation? [Completeness, Quickstart §4]
- [x] CHK004 Are canonical local CI, focused server tests, Swift build/tests, readiness regeneration, and diff check listed as closeout gates? [Completeness, Quickstart §2/§6/§7/§9]
- [x] CHK005 Are production rollout claims explicitly excluded without separate journey evidence? [Completeness, Spec §FR-016]

## Requirement Clarity

- [x] CHK006 Is the difference between `infra_smoke_ready`, `mvp_loop_ready`, `internal_pilot_candidate`, and broader rollout claims preserved? [Clarity, Contract readiness-claim]
- [x] CHK007 Are expected outcomes defined for empty, blocked, and deferred production review states? [Clarity, Spec §US1]
- [x] CHK008 Are route/status evidence requirements clear without requiring private content dumps? [Clarity, Contract owner-review-live-proof]

## Requirement Consistency

- [x] CHK009 Do live proof requirements align with existing production-smoke helper boundaries? [Consistency, Research §session primitives]
- [x] CHK010 Do evidence paths avoid contradicting forbidden-content policy from 035 and the constitution? [Consistency, Plan §Constraints]
- [x] CHK011 Does the installed-app requirement stay aligned to `/Applications/2brain Rec.app` instead of changing app identity mid-validation? [Consistency, Research §installed desktop]

## Acceptance Criteria Quality

- [x] CHK012 Can each production proof state be recorded as pass, blocked, empty, or deferred with a named reason? [Measurability, Data Model §OwnerReviewProof]
- [x] CHK013 Can readiness artifacts be regenerated and compared for agreement across docs/status/changelog? [Measurability, Contract readiness-claim]
- [x] CHK014 Can cleanup failure be treated as a blocker rather than silently accepted? [Acceptance Criteria, Contract owner-review-live-proof]

## Scenario Coverage

- [x] CHK015 Are browser extension/ad-block/navigation failures allowed as blocker evidence without being mistaken for product readiness? [Edge Case, Spec §Edge Cases]
- [x] CHK016 Are remote production constraints kept separate from local fixture-backed tests and desktop runtime proof? [Coverage, Plan §Target Platform]
- [x] CHK017 Is the installed-app cabinet connection requirement specified as persistent or packaged configuration rather than process environment only? [Completeness, Spec §FR-017, Research §installed desktop cabinet connectivity]
