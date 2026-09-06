# Infrastructure and Orchestration Checklist: Повторная обработка записи

## Durable admission

- [x] The predecessor/successor fence survives lost responses and duplicate delivery
- [x] Existing active-attempt constraints remain authoritative
- [x] Same-predecessor replay and stale-predecessor conflict are distinguished
- [x] Quota remains revision-scoped and idempotent
- [x] Durable workflow state precedes Temporal start

## Temporal and provider safety

- [x] Every new payload carries the exact processing workflow row ID
- [x] Legacy histories have a bounded compatibility path
- [x] Workflow command order does not change
- [x] MediaScribe job idempotency and unknown-POST reconciliation remain
- [x] Manual retry wakes the same workflow/job and fences stale generations
- [x] No new workflow type, queue, scheduler or dependency is introduced

## Result continuity

- [x] Result import remains atomic under the meeting lock
- [x] Superseded workflow, revision, fingerprint and deletion fences remain
- [x] Only complete transcript plus diarization is customer-visible
- [x] All customer readers use the same selector
- [x] Outcomes remain independently published

## Validation

- [x] Migration upgrade/downgrade and index behavior are testable
- [x] Temporal replay and delayed-old-activity scenarios are required
- [x] Cross-channel consistency and restart scenarios are required
- [x] Production execution remains separately gated
