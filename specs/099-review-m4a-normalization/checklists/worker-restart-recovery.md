# Worker-Interrupted Startup Recovery Requirement Checklist

**Purpose**: Requirement-quality check for the 2026-07-17 production hotfix.
It does not claim runtime validation.

## Scope And Clarity

- [x] CHK001 Is the automatic recovery trigger limited to the durable machine-readable `worker_interrupted` reason? [Clarity, Spec §Clarifications 2026-07-17, FR-043]
- [x] CHK002 Does the requirement state that no user or workspace administrator performs a retry or repair action? [User value, Spec §Clarifications 2026-07-17, FR-023, FR-043]
- [x] CHK003 Does it preserve the original record/job lineage rather than create replacement work or media? [Consistency, Spec §FR-007, FR-010, FR-024, FR-043]

## Safety And Boundaries

- [x] CHK004 Is long scheduled backoff preserved for every reason other than `worker_interrupted`? [Safety, Spec §FR-011, FR-023, FR-043]
- [x] CHK005 Is recovery constrained to worker startup rather than each periodic reconciliation pass? [Bounded behavior, Plan §2026-07-17 Production Recovery Hotfix]
- [x] CHK006 Does the hotfix exclude schema, source-custody, playback-route and native-app changes? [Scope, Plan §2026-07-17 Production Recovery Hotfix]
- [x] CHK007 Is the existing lock/audit/lease/dispatch lifecycle retained rather than bypassed? [Lifecycle, Plan §2026-07-17 Production Recovery Hotfix]

## Acceptance Quality

- [x] CHK008 Is success measurable for both immediate interrupted-job dispatch and non-preemption of another retry reason? [Measurability, Spec §SC-023]

## Notes

- The checklist is complete for requirement quality. Runtime proof is owned by
  T117–T120 and must remain metadata-only.
