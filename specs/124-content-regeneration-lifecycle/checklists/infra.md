# Requirements Quality Checklist: Infrastructure and Recovery

**Purpose**: Validate that persistence, external dispatch, migration and release requirements are complete and operationally safe.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK001 Are migration expand/backfill/enforce/cleanup phases defined? [Completeness, Plan §Migration, Data Model §Migration]
- [X] CHK002 Is durable dispatch required when a database intent commits before Temporal/provider start? [Completeness, Spec §FR-021, Contract §processing-lineage]
- [X] CHK003 Are backup/restore, rollback and RLS gates named before production? [Completeness, Plan §Release Gate, Quickstart]
- [X] CHK004 Are object-store purge journal states and reconciliation requirements defined? [Completeness, Contract §deletion-generation]

## Requirement Clarity and Consistency

- [X] CHK005 Is the idempotency key stable across retries but distinct for explicit same-format refresh? [Clarity, Spec §FR-006/014]
- [X] CHK006 Are terminal, retryable and cancelled dispatch states distinguishable? [Clarity, Data Model §DispatchIntent]
- [X] CHK007 Are old workflow callbacks prohibited from changing newer revision aggregates? [Consistency, Spec §FR-003/023, Contract §processing-lineage]
- [X] CHK008 Does the release gate distinguish local CI evidence from production/RLS evidence? [Consistency, Plan §Release Gate, Quickstart]

## Scenario and Edge Coverage

- [X] CHK009 Are Temporal outage, worker restart, duplicate delivery and restore/reconcile paths covered? [Coverage, Spec §User Story 7, Edge Cases]
- [X] CHK010 Are concurrent active-run/job/candidate creation and quota pressure covered? [Coverage, Spec §FR-023/024]
- [X] CHK011 Are migration rollback and legacy-row compatibility stop conditions explicit? [Edge Case, Data Model §Migration]

## Acceptance Quality

- [X] CHK012 Is “no stranded queued candidate” tied to a defined recovery window and observable terminal state? [Measurability, Spec §SC-004]
- [X] CHK013 Are exact commands and expected evidence named in the quickstart and not just described as “run tests”? [Acceptance, Quickstart]
