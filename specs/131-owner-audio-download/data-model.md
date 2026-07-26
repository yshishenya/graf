# Data Model: Owner-default audio egress

**Feature**: `131-owner-audio-download`

## Persistent model

No tables, columns, indexes, migrations, object formats, or retention records
are added. The existing `MeetingArtifactPolicy` row remains the persisted
policy snapshot:

- `audio_download`: `allowed`, `owner_only`, or `disabled`.
- `transcript_download`, `summary_download`, `package_export`: unchanged.
- `policy_source`: existing string source. This feature treats
  `meeting_default` and `workspace_default` as implicit defaults;
  `meeting_override` is the explicit per-meeting privacy source. Existing
  `test_fixture` and unknown sources remain conservative.

The source distinction is important because the value `disabled` alone cannot
tell whether a user deliberately denied an individual meeting or whether the
row merely carries a workspace/default setting.

## Effective audio policy

The persisted value is not rewritten. The egress layer derives the effective
value immediately before access-state evaluation:

| `policy_source` | Stored `audio_download` | Effective value | Owner | Permitted non-owner |
|---|---|---|---|---|
| missing row / `meeting_default` | `disabled` | `owner_only` | available when artifact ready | owner-only denial |
| `workspace_default` | `disabled` | `owner_only` | available when artifact ready | owner-only denial |
| `meeting_override` | `disabled` | `disabled` | denied | denied |
| `test_fixture` or unknown | `disabled` | `disabled` | denied | denied |
| any accepted source | `owner_only` | `owner_only` | available when artifact ready | owner-only denial |
| any accepted source | `allowed` | `allowed` | available when artifact ready | existing access/policy result |
| any source | unknown value | unchanged/blocked | denied | denied |

The meeting owner is determined by the existing `AccessDecision.state ==
"owner"`; the feature does not infer ownership from request headers or a
client-provided field.

## Derived view state

`ArtifactEgressState` remains unchanged. For audio it continues to expose
`available`, `policy_blocked`, `owner_only`, or `missing` with the existing
labels, reasons, and `download`/`disabled` action values. The same derived state
feeds server-rendered web and embedded macOS detail pages and is recomputed for
the direct download request.

## Audit model

`MeetingEgressAuditEvent` remains unchanged and metadata-only. An implicit owner
download records the existing `download_requested` and
`download_stream_prepared` events. Explicit denial, non-owner denial, missing
artifact, deletion, and storage failures use the existing bounded denial
events. No audio bytes, transcript text, object keys, signed URLs, credentials,
or private paths are added.

## State invariants

1. Owner-default never changes transcript, summary, or package policy.
2. An effective `owner_only` decision cannot be bypassed by a direct URL.
3. The effective policy is evaluated after the current access and deletion
   re-check and before storage headers/bytes are exposed.
4. Persisted default policy rows are not mutated as a side effect of viewing or
   downloading.
