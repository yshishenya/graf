# Security And Privacy Requirements Checklist: Apple Voice Processing Spike

**Purpose**: Validate privacy, diagnostics, and evidence-safety requirements before tasks and implementation
**Created**: 2026-06-22
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are diagnostics requirements complete for success, blocked, unproven, route-change, Stop/quit, and redaction outcomes? [Completeness, Spec §US3]
- [x] CHK002 Are forbidden evidence classes explicitly listed, including raw audio, transcript text, credentials, signed URLs, private paths, and meeting content? [Completeness, Spec §FR-015, Contract §Diagnostics]
- [x] CHK003 Are content-bearing Langfuse, MediaScribe, and direct desktop egress risks excluded or kept out of scope? [Scope, Plan §Constitution Check]
- [x] CHK004 Are derived/candidate artifact lifecycle risks identified before any candidate audio can be accepted? [Completeness, Plan §Constitution Check]

## Requirement Clarity

- [x] CHK005 Is `diagnosticSafe` defined as a required field for spike result and evidence models? [Clarity, Data Model §AppleProcessingCandidate, Contract §Apple Processing Spike Result]
- [x] CHK006 Are user/system-controlled Mic Mode states labeled clearly enough to avoid implying hidden system setting changes? [Clarity, Spec §FR-014]
- [x] CHK007 Are safe reason code requirements defined for blocked and unproven results? [Clarity, Spec §SC-005]

## Requirement Consistency

- [x] CHK008 Do diagnostic requirements align with the constitution's metadata-only and secret-discipline principles? [Consistency, Constitution §III, Plan §Constitution Check]
- [x] CHK009 Are privacy requirements consistent between spec, data model, diagnostics contract, and quickstart? [Consistency, Spec §FR-015, Contract §Diagnostics, Quickstart §Package Inspection]
- [x] CHK010 Are original evidence preservation requirements consistent with deletion/lifecycle accounting constraints? [Consistency, Spec §FR-005, Plan §Post-Design Constitution Check]

## Scenario Coverage

- [x] CHK011 Are requirements defined for unsafe runtime-only private captures so they cannot be committed or pasted into issues/PRs? [Coverage, Contract §Diagnostics]
- [x] CHK012 Are unbounded platform logs or device-private data excluded from committed diagnostics? [Coverage, Contract §Diagnostics]
- [x] CHK013 Are diagnostics required to remain useful after redaction through bounded codes/classes? [Measurability, Contract §Diagnostics]

## Notes

- Checklist is complete after reviewing `spec.md`, `plan.md`, `data-model.md`,
  and `contracts/diagnostics-contract.md`.
