# Processing Analytics Contract Tests

**Feature**: `195-processing-recovery`
**Lane**: metadata-only spec validation; no runtime processing or provider
access is part of this file.

The executable companion is
[`test_processing_analytics_contract.py`](test_processing_analytics_contract.py).
It reads only the local schema, synthetic fixtures, and the event/KPI contract.
It does not import `twobrain_rec_server`, open a database, call Temporal, call
MediaScribe, or send an analytics event.

## Focused command

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python specs/195-processing-recovery/validation/test_processing_analytics_contract.py
```

If the repository test runner is used, the same file can be selected without
expanding the processing test surface:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  specs/195-processing-recovery/validation/test_processing_analytics_contract.py
```

## Contract test matrix

| ID | Check | Expected evidence |
| --- | --- | --- |
| A-001 | Parse the strict JSON Schema and require `additionalProperties=false` at the envelope and dimension level. | Schema is valid JSON; no unbounded fields. |
| A-002 | Validate one safe synthetic rollup for every event variant. | All fixtures use only bounded dimensions and positive aggregate counts. |
| A-003 | Reject an unknown dimension on an otherwise valid event. | Event-specific allowlist fails closed. |
| A-004 | Reject meeting, revision, attempt, provider-job, request, identity, path, credential, transcript, summary, and raw-payload keys. | Metadata-only guard reports a contract failure. |
| A-005 | Check event catalog/documentation coverage. | All ten event names and all requested KPI names appear in the contract. |
| A-006 | Check first usable transcript formula and dimensions. | Numerator is gated by transcript+diarization; summary/playback states remain independent. |
| A-007 | Check retry/reconciliation dimensions. | External hint is only a bounded source category; same-key safety and retry outcome stay measurable without an identifier. |
| A-008 | Check manual command outcomes. | Accepted, in-flight, stale, and duplicate-suppressed requests are distinct; completion is one claimed check. |
| A-009 | Check terminal/support dimensions. | Terminal rows have a next action; support `unavailable` is an explicit failure bucket; no countdown is represented as success. |
| A-010 | Check surface parity coverage. | `web_list`, `web_detail`, and `embedded_desktop_detail` all have a matching fixture observation. |
| A-011 | Check production denominator boundary. | `contract_test` is documented as excluded from production KPI denominators. |
| A-012 | Check deletion-safe emission rule in the contract. | Late or stale fenced writes produce no milestone event; no raw deletion/provider receipt is fixture data. |

## Negative cases for the later runtime implementation

These cases belong in the future runtime tests for T046/T047; they are written
here so the metadata slice has an exact handoff and does not silently broaden
scope:

1. An event with a meeting/revision/attempt identifier, title, filename, path,
   credential, provider detail, transcript, summary, or free text is rejected
   before persistence and egress.
2. A duplicate lifecycle transition in the same internal milestone boundary
   increments no aggregate count twice.
3. A late result after a deletion-epoch change produces no first-usable,
   retry-success, terminal, or parity milestone.
4. A manual command returning `already_in_flight`, `stale_schedule`, or
   `duplicate_suppressed` produces no second `processing_manual_check_completed`
   count.
5. A retry with `new_attempt_created=false` retains the same-key recovery
   interpretation; a new business attempt is represented only by the bounded
   `attempt_kind` dimension on a later lifecycle event.
6. A surface mismatch is retained as `parity_result=mismatch` with a bounded
   `mismatch_reason`; it is not discarded to inflate the parity rate.

## Evidence rules

- Keep committed fixtures synthetic and categorical. Do not add raw audio,
  transcript, provider JSON, signed URLs, request bodies, private meeting
  titles, or real identifiers.
- Record test counts and the exact command, not payload dumps.
- Do not claim provider delivery, production collection, or deletion from an
  analytics sink based on this spec-level test alone.
- If the later runtime implementation changes event names or dimensions, update
  the schema, catalog, KPI formulas, fixtures, and tests together and bump the
  schema version when compatibility is not additive.
