# Task Quality Checklist: Live Route Stability

**Purpose**: Validate that `tasks.md` is complete, clear, traceable, dependency-ordered, and safe to pass into `$speckit-analyze`.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the quality of the task plan as written. It does not test implementation behavior.

## Traceability

- [ ] CHK001 Are all five user stories represented as separate task phases with clear story goals and independent test criteria? [Traceability, Tasks §Phases 3-7, Spec §User Stories]
- [ ] CHK002 Are P1 route preservation, autorepair, recording timeline, and self-inflicted drop prevention requirements traceable to task groups before the P2 evidence story? [Traceability, Tasks §Phases 3-7, Spec §FR-001-FR-051]
- [ ] CHK003 Are contract artifacts from `contracts/` reflected in foundational or story-specific tasks without leaving any contract unowned? [Coverage, Tasks §Phase 2, Plan §Phase 1 Design Decisions]
- [ ] CHK004 Are success criteria for 30-minute, 75-minute, user-action audit, timing tiers, and timeline alignment represented in task validation outputs? [Completeness, Tasks §Phase 8, Spec §SC-001-SC-026]

## Dependency Ordering

- [ ] CHK005 Are setup tasks limited to scaffolding and evidence structure rather than story implementation? [Clarity, Tasks §Phase 1]
- [ ] CHK006 Are foundational model, contract, redaction, and evidence-store tasks clearly marked as blocking prerequisites for all user stories? [Consistency, Tasks §Phase 2]
- [ ] CHK007 Are tests listed before implementation tasks inside each user story phase where TDD is required by risk and plan? [Ordering, Tasks §Phases 3-7, Plan §Implementation Approach]
- [ ] CHK008 Are dependencies between US1, US2, US3, US4, and US5 described clearly enough to avoid implementing aggregate evidence before prerequisite route facts exist? [Clarity, Tasks §Dependencies]

## Task Specificity

- [ ] CHK009 Does every task include a concrete file path and a specific outcome rather than a vague area of work? [Clarity, Tasks §Format]
- [ ] CHK010 Are `[P]` markers limited to tasks that touch different files and do not depend on incomplete prior tasks? [Consistency, Tasks §Parallel Opportunities]
- [ ] CHK011 Are validation and evidence documentation tasks specific enough to produce reviewable artifacts under `specs/019-live-route-stability/evidence/`? [Completeness, Tasks §Phases 3-8]
- [ ] CHK012 Are route engine tasks scoped clearly enough to avoid hidden changes to realtime callbacks, physical-device selection, or unrelated capture behavior? [Scope, Tasks §US1-US4, Plan §Constraints]

## Scope Protection

- [ ] CHK013 Are tasks clear that `019` must not implement `020` speaker-to-mic leakage or echo policy? [Scope, Tasks §Scope Guardrails, Spec §Scope Boundary]
- [ ] CHK014 Are tasks clear that backend ingest, desktop transfer queues, transcription, MediaScribe, Langfuse, analytics, dashboard, sharing, retention, and deletion work remain out of scope? [Scope, Tasks §Scope Guardrails, Spec §Scope Boundary]
- [ ] CHK015 Are Bluetooth and AirPods-class routes represented as backlog/not accepted evidence rather than implementation acceptance tasks? [Scope, Tasks §US2, Tasks §US5, Spec §FR-042]
- [ ] CHK016 Are visible indicator and one-action stop protections represented in task scope when autorepair and recording overlap? [Coverage, Tasks §US3, Constitution §II]

## Analyze Readiness

- [ ] CHK017 Are task IDs sequential and formatted consistently enough for `$speckit-analyze` to compare tasks against spec, plan, and constitution? [Consistency, Tasks §Format]
- [ ] CHK018 Are open questions, assumptions, and risk boundaries represented in tasks or scope guardrails instead of requiring hidden implementation decisions? [Completeness, Tasks §Implementation Strategy, Spec §Assumptions]
- [ ] CHK019 Are quickstart validation scenarios represented in tasks without replacing quickstart with an implementation-only test script? [Consistency, Tasks §Phase 8, Quickstart §Acceptance Summary]
- [ ] CHK020 Are privacy and diagnostic redaction requirements represented before any evidence aggregation or diagnostic bundle task? [Ordering, Tasks §Phase 2, Tasks §US5, Constitution §III]
