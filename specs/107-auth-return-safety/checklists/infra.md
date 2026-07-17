# Infrastructure And Diagnostics Requirements Checklist: Safe Browser Login Returns and Callback Diagnostics

**Purpose**: Validate that runtime logging and Docker-boundary requirements are complete, measurable, and bounded from deployment work.
**Created**: 2026-07-17
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [browser auth return contract](../contracts/browser-auth-return.md)

## Logging Requirement Completeness

- [x] CHK001 Do the requirements identify both query-bearing server access output and arbitrary request-header capture as independent diagnostic exposure paths? [Completeness, Plan §Summary, Research §Decision 5]
- [x] CHK002 Is the retained metadata set explicitly named so removal of raw request material does not make support observability undefined? [Clarity, Spec §FR-010, Contract §Callback diagnostics contract]
- [x] CHK003 Is the prohibition broad enough to cover authorization codes, callback state, cookies, session/provider tokens, raw query values, and arbitrary headers? [Coverage, Spec §FR-009, Contract §Callback diagnostics contract]
- [x] CHK004 Is the route representation constrained to a UUID-templated path so identifiers do not become an accidental log data channel? [Security, Clarity, Contract §Callback diagnostics contract]

## Runtime And Validation Boundaries

- [x] CHK005 Is the production runtime command treated as a source-controlled contract with a repeatable assertion, rather than an undocumented operational assumption? [Completeness, Plan §Validation Plan]
- [x] CHK006 Is the diagnostic validation requirement defined against a real process boundary with synthetic markers in every relevant request location? [Measurability, Spec §SC-004, Quickstart §Required scenarios]
- [x] CHK007 Is the requirement clear that safe structured request events remain available after the access-log change? [Consistency, Spec §FR-010, Contract §Callback diagnostics contract]
- [x] CHK008 Are external reverse-proxy logging, retention, rotation, and deletion identified as a separate authorized operational decision rather than implied implementation work? [Scope, Assumption, Research §Decision 6]
- [x] CHK009 Is the no-release/no-deploy boundary explicit despite the Dockerfile change, including the user's parallel-work gate? [Dependency, Plan §Release Gate, Quickstart §Scope boundary]

## Non-Functional Requirements

- [x] CHK010 Is redirect processing constrained to bounded metadata/access evaluation, avoiding transcript, media, or full review loading on an authentication callback? [Performance, Privacy, Plan §Performance Goals]
- [x] CHK011 Are focused tests and canonical local CI both required at their appropriate stages, without treating a deployment smoke as a substitute? [Validation Coverage, Plan §Validation Plan, Quickstart §Closeout gate]

## Notes

- Review pass 1: 11/11 requirement-quality questions pass. The plan separates source-controlled runtime hardening from production operations and defines a reproducible metadata-only logging proof.
