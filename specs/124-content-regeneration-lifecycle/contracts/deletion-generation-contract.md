# Contract: Deletion, Retention and Generation Races

## Tombstone fence

Every processing, generation, preview, accept, export and share operation
captures the meeting deletion epoch before work. It checks the epoch again:

1. immediately before provider/storage egress;
2. immediately after the egress returns;
3. before committing a result, candidate or current-pointer change.

If the epoch changed, the operation does not publish content and records only a
safe blocked/cancelled state.

## Controlled artifact classes

The deletion report must account separately for:

- media objects and processing artifacts;
- transcript/diarization segments;
- outcome items and candidate previews;
- generation-call request/transcript/raw-response fields;
- metadata-only correlation and audit records;
- provider/external copies outside GRAF control;
- backups with an explicit expiry policy.

Completed content-bearing Generation Calls, Langfuse observations and Temporal
History are explicitly `observability_retained` under the operator-approved
internal-MVP retention policy required by the constitution. They are not
metadata-only and are not deleted by meeting deletion. The report must never
label them `metadata_retained`; `metadata_retained` is reserved for rows with no
content. GRAF-controlled meeting copies still use the purge journal below.

## Storage purge journal

Object deletion is represented by a durable per-artifact state:

```text
pending → deleting → purged
                   ├→ retryable_failed → deleting
                   └→ terminal_unknown
```

Database metadata and journal transitions may be committed independently of
object deletion. A reconciler retries missing objects and never claims complete
purge without verification. DB rollback cannot resurrect an already deleted
object.

## Race outcomes

| Race | Required result |
|---|---|
| delete vs processing import | delete wins; no new result/segments |
| delete vs candidate generation | provider call is blocked/cancelled where possible; returned content is discarded |
| delete vs candidate accept | 409/blocked; current pointer unchanged |
| delete vs export/share | action stops or reports external copy boundary; no new GRAF publication |
| late worker callback | no-op against old epoch; metadata-only event |
| provider/observability delivery delayed | retention report says what remains and why |
