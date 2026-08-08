# Data model: transcript-export-recovery

## Existing entities used

| Entity | Relevant fields | Invariant preserved |
|---|---|---|
| `MeetingArtifactPolicy` | four egress values, `policy_source` | A stored `meeting_override` wins; absent policy is an in-memory default only. |
| `Meeting` | `current_outcome_set_id`, deletion state/epoch, immutable lifecycle status | A current accepted outcome is never replaced by an automatic baseline. |
| `MediaRevision` | accepted/immutable revision number and fingerprint | An outcome must reference the latest accepted immutable source. |
| `ProcessingResult` | imported status, revision ID, result version/hash, transcript availability | Export uses the result selected by the existing latest-result fence. |
| `TranscriptSegment` | stable UUID and stored sequence | The segment UUID is the source identity; its stored sequence is canonical. |
| `MeetingOutcomeSet` | candidate ID, result/revision/hash, status, `revision_state`, accepted timestamp | Only available/partial accepted sets can be current/exportable. |
| `MeetingOutcomeGenerationAttempt` | candidate ID, status, source provenance | A system-published baseline is marked accepted; a later AI candidate remains reviewable. |

## Effective policy matrix

| Raw source/value | Owner | Permitted non-owner |
|---|---|---|
| no row / `meeting_default` + `disabled` | `owner_only` | blocked |
| `workspace_default` + `disabled` | `owner_only` | blocked |
| `meeting_override` + `disabled` | blocked | blocked |
| explicit `owner_only` | allowed | blocked |
| explicit `allowed` | allowed | allowed subject to meeting access |

The same effective value is used by capability calculation, artifact-state
projection and the direct export route. No client-side-only permission path is
introduced.

## Outcome state transition

```text
ready imported result
        |
        v
deterministic baseline
        |
        +-- no current accepted outcome + trusted import/reconcile --> accepted + current pointer
        |
        +-- current accepted outcome exists -------------------------> candidate, owner review
        |
        +-- explicit/manual AI candidate -----------------------------> candidate, owner review
```

The transition is idempotent: a repeated reconcile sees the current pointer and
does not create or replace an accepted outcome. Revision/result/source-hash
fences run before either branch.

## AI source reference normalization

Input `{transcript_segment_id, sequence}` is valid only when the ID belongs to
the pinned transcript and the sequence is a non-negative integer. With a pinned
ID-to-sequence mapping, the stored output is
`{transcript_segment_id, sequence: mapping[id], evidence_kind: "segment"}`.
An unknown ID or invalid structure still fails closed.
