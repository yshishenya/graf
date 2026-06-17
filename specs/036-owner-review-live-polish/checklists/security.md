# Security Requirements Quality Checklist: Owner Review Live Polish

**Purpose**: Validate auth, secret, privacy, and evidence requirements before implementation
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are protected owner review resources covered for list, detail, and governance states? [Completeness, Spec §FR-001/FR-002]
- [x] CHK002 Are unauthenticated, expired, invalid, denied, and blocked session states specified without leaking meeting existence? [Coverage, Spec §FR-003]
- [x] CHK003 Are temporary smoke-session issuance, token handling, and cleanup requirements documented? [Completeness, Plan §Research, Contract owner-review-live-proof]
- [x] CHK004 Are forbidden committed evidence classes complete for tokens, cookies, signed URLs, account identifiers, private transcript text, raw audio, provider payloads, and local paths? [Completeness, Spec §FR-013]
- [x] CHK005 Are desktop credential boundaries specified so the macOS app does not store MediaScribe or owner-review auth secrets? [Consistency, Constitution III, Spec §Assumptions]

## Requirement Clarity

- [x] CHK006 Is "metadata-safe evidence" defined with concrete allowed and forbidden examples? [Clarity, Contract owner-review-live-proof]
- [x] CHK007 Is the distinction between header-based API proof and browser owner-review proof explicit? [Clarity, Research §browser access]
- [x] CHK008 Is the required cleanup outcome clear when temporary sessions are created? [Clarity, Data Model §OwnerReviewProof]
- [x] CHK009 Are safe failure codes and blocker states named enough to avoid vague "auth failed" evidence? [Clarity, Data Model §OwnerReviewProof]

## Requirement Consistency

- [x] CHK010 Do auth proof requirements align with existing RLS/session/device context rules rather than bypassing them? [Consistency, Plan §Technical Context]
- [x] CHK011 Do evidence restrictions align across spec, plan, data model, contracts, and quickstart? [Consistency, Spec §FR-013, Quickstart §8]
- [x] CHK012 Do privacy requirements avoid conflicting with the need for live owner proof? [Consistency, Spec §US1]

## Acceptance Criteria Quality

- [x] CHK013 Can the owner-review proof be objectively classified as ready, empty, blocked, or deferred? [Measurability, Data Model §OwnerReviewProof]
- [x] CHK014 Can forbidden-content scan expectations be objectively evaluated before closeout? [Measurability, Quickstart §8]
- [x] CHK015 Is readiness downgrade behavior specified when only partial auth proof is available? [Acceptance Criteria, Contract owner-review-live-proof]

## Scenario Coverage

- [x] CHK016 Are recovery requirements documented for cleanup failure or unremoved temporary sessions? [Coverage, Data Model §OwnerReviewProof]
- [x] CHK017 Are private-content live screenshots intentionally excluded unless sanitized or synthetic? [Coverage, Spec §Clarifications]
- [x] CHK018 Are destructive governance actions excluded from proof unless separately authorized? [Coverage, Spec §FR-016]
- [x] CHK019 Are desktop cabinet connection requirements explicit about not hard-coding or shipping secret-bearing owner tokens? [Consistency, Research §installed desktop cabinet connectivity]
