# Infra And Runtime Requirements Checklist: MVP Loop Live Evidence

**Purpose**: Validate that requirements define the infrastructure/runtime
evidence needed for the live MVP loop decision without expanding deployment
scope.
**Created**: 2026-06-16
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are server readiness tests, relevant macOS tests, desktop artifact validation, app process path checks, and forbidden-content scans required in the validation log? [Completeness, Spec §FR-009]
- [x] CHK002 Are backend readiness artifacts and current deployment evidence included in the single claim summary scope? [Completeness, Spec §FR-005]
- [x] CHK003 Are issue sync and tracker evidence required for closeout traceability? [Completeness, Quickstart §7]
- [x] CHK004 Are production deploy changes explicitly excluded unless separately specified? [Completeness, Spec §Out Of Scope]

## Requirement Clarity

- [x] CHK005 Is the installed app proof path specific enough for reproducible macOS permission checks? [Clarity, Spec §FR-001]
- [x] CHK006 Is the evidence pack location and file structure defined clearly in the plan and contracts? [Clarity, Plan §Project Structure]
- [x] CHK007 Are validation outcomes allowed to be pass, fail, blocked, or not applicable with blocker notes? [Clarity, Data Model §ValidationRun]

## Requirement Consistency

- [x] CHK008 Do quickstart commands align with the plan's selected existing validation tools? [Consistency, Plan §Testing, Quickstart §5]
- [x] CHK009 Does the no-new-deployment boundary align with the readiness claim contract? [Consistency, Spec §FR-012, Contract §Claim Rules]

## Acceptance Criteria Quality

- [x] CHK010 Are server and macOS validation expectations measurable by command outputs? [Acceptance Criteria, Spec §SC-005]
- [x] CHK011 Is stale next-slice recommendation removal measurable and testable? [Acceptance Criteria, Spec §SC-002]
