# Data Model: Canonical Transcript And Summary Export

This feature adds no database table or migration. Durable truth remains in the
existing meeting, processing result, raw transcript/diarization, speaker-name,
outcome, policy, and egress-audit models. Export snapshot/artifact types are
immutable request-scoped values.

## Export Selection

| Field | Type | Rule |
|---|---|---|
| `content_scope` | `transcript | summary | combined` | Combined requires both policies and both selected artifacts ready. |
| `format` | `txt | md | csv | xlsx | json | srt` | Server allowlist; CSV/SRT cannot represent combined content. |
| `processing_result_id` | UUID | Required and must belong to the meeting, workspace, and a terminal exportable result. |
| `outcome_set_id` | UUID or null | Required for summary/combined and must be the current stored outcome set for the selected result. |
| `include_speaker_labels` | bool | Presentation option only; machine rows retain stable speaker identity. |
| `include_timestamps` | bool | Presentation option only; machine rows/cues always retain timing. |
| `include_evidence` | bool | Summary presentation option; source references remain in JSON/XLSX metadata when selected. |

Validation rejects unknown fields, incompatible format/scope, stale or foreign
revision ids, partial results, missing stored summary content, and unsupported
MIME/extension aliases.

## Raw Transcript Source Row

Existing immutable/append-only `TranscriptSegment` or equivalent imported
source row.

| Field | Rule in snapshot |
|---|---|
| source id, sequence, start/end, text | Copied exactly; never rewritten or dropped from JSON raw fidelity. |
| processing result | Must equal the selected pinned result. |
| source role | Preserved and forms a canonical boundary. |
| speaker/provider provenance | Normalized to GRAF-owned attribution fields; provider secrets/job details are excluded. |
| invalid/empty state | Retained in raw JSON with a safe reason; cannot become merge evidence or a synthetic utterance. |

## Canonical Speaker Turn

Derived by the shared feature 113 rule from one selected result.

| Field | Type | Rule |
|---|---|---|
| `turn_id` | string | Deterministic from selected result plus ordered source ids. |
| `sequence` | integer | Stable source order. |
| `start_ms`, `end_ms` | integer | Exact normalized interval; no 60-minute wrap. |
| `text` | string | Ordered source text; no pause text. |
| `speaker_key` | string | Stable GRAF identity or explicit unknown key. |
| `speaker_label` | string | Saved display name/automatic label/unknown projection. |
| `attribution_state` | enum | `confirmed | unconfirmed | unknown`. Unknown is never confirmed `SPEAKER_00`. |
| `source_role` | enum/string | Preserved canonical track boundary. |
| `source_segment_ids` | list[string] | Ordered, non-empty, same selected result. |
| `overlap` | bool | True when source timing overlaps another turn; prevents display merge. |
| `timing_state` | enum | `valid | invalid`; invalid rows stay raw-only and cannot become SRT cues. |

Adjacent confirmed rows merge only when speaker key, attribution state, source
role, and selected result match; timing is valid/non-overlapping; and every
pairwise gap is `0 <= gap <= 1.000` seconds. Unknown/unconfirmed rows are
non-mergeable singleton turns. A gap above the threshold is only a time jump.

## Human Display Group

Ephemeral TXT/MD-only projection.

| Field | Rule |
|---|---|
| `speaker_key`, `speaker_label`, `source_role` | Must match every child turn. |
| `turn_ids` | Ordered canonical children; never hidden from timestamps. |
| boundary | Speaker/attribution/source/result/overlap/invalid/long-gap changes start a new group. |

No display group appears in CSV, XLSX transcript rows, JSON canonical turns, or
SRT cues.

## Summary Revision Projection

Request-scoped view of existing `MeetingOutcomeSet` and ordered
`MeetingOutcomeItem` rows.

| Field | Source/rule |
|---|---|
| `outcome_set_id` | Stable saved set identity. |
| `source_processing_result_id` | Must equal the selected transcript result for combined export. |
| `revision_token` | Outcome-set id + content hash + generator/template version; included in snapshot identity. |
| `status` and category states | Preserve available/partial/deferred/failed/unsafe truth. |
| `generator_kind/version` | Provenance only; no provider credential or prompt content. |
| `items` | Ordered category/sequence/state/text/owner/due date/truth label. |
| `source_refs` | Existing raw segment refs plus resolved canonical turn ids when exact; unresolved refs stay explicit. |

Export never calls the generator, replaces items, repairs missing text, invents
owner/due dates, or chooses a different outcome set after snapshot creation.

## Export Snapshot

Frozen aggregate consumed by every serializer.

| Field | Rule |
|---|---|
| `schema_version` | Versioned provider-neutral JSON/export contract. |
| `renderer_version` | Identifies output policy/escaping behavior. |
| meeting metadata | Safe title, language, duration, workspace-local timestamps; no private paths/URLs. |
| `processing_result_id` | Pinned terminal result. |
| `turn_policy_version` | Shared canonical derivation version. |
| `raw_segments` | Complete selected-result fidelity for JSON only. |
| `canonical_turns` | Ordered canonical rows for every format. |
| `summary` | Selected stored projection or explicit absence/status. |
| `content_scope/options` | Exact validated request. |

Snapshot canonical bytes are deterministic for identical stored inputs and
selection. Delivery time, actor, audit ids, request ids, and response headers do
not enter canonical payloads.

## Export Policy Decision

Derived from existing feature 017 access and artifact policy.

| Scope | Requirement |
|---|---|
| transcript | Current meeting read + transcript export allowed + terminal result + deletion inactive. |
| summary | Current meeting read + summary export allowed + current stored outcome ready + deletion inactive. |
| combined | Both transcript and summary decisions allowed for the same pinned result. |

Every capability read and file request recomputes the decision server-side.
The UI state is informative, never authority.

## Ephemeral Export Artifact

| Field | Rule |
|---|---|
| filename/media type/bytes | Built from allowlisted format and sanitized meeting metadata. |
| byte length/content hash | Computed before completion audit. |
| lifecycle | Exists only in request memory until the response is returned. |
| persistence/expiry/storage key | Absent in this slice. |

If serialization or completion-audit persistence fails, the bytes are discarded
and no response content is sent.

## Export Egress Event

Existing `MeetingEgressAuditEvent`, with allowlisted metadata extended for:
content scope, format, selected result id, outcome-set id/one-way revision fingerprint,
schema/renderer version, policy reason, outcome, and byte length. It never
stores raw/canonical text, summary text, source references, speaker names,
credentials, provider ids, signed URLs, object keys, or private paths.

## State transitions

```text
request
  -> denied (access/policy/readiness/revision/deletion)
  -> allowed -> snapshot_built -> serialized -> audited_completed -> response
                                      |                 |
                                      -> failed         -> audit_unavailable
```

There is no durable export state. Browser progress is a truthful UI state for
the in-flight request. A retry builds a new snapshot only after rechecking all
current gates.

## Deletion and retention

- Deletion-in-progress blocks new capability/file requests.
- No export file is retained inside GRAF, so existing source deletion covers all
  controlled data used by this slice.
- Audit metadata follows the existing audit retention policy.
- UI/copy states that already downloaded files cannot be revoked or erased by
  later GRAF deletion.
