# Contract: Canonical Content Export API And UI

This additive contract does not change existing raw/plain transcript downloads
or feature 017 package-manifest routes.

## Capability endpoint

`GET /api/v1/cabinet/meetings/{meeting_id}/content-exports`

Returns metadata only after current authenticated meeting access is resolved.

```json
{
  "processing_result_id": "uuid",
  "outcome_set_id": "uuid-or-null",
  "transcript": {"state": "available", "reason": null},
  "summary": {"state": "missing", "reason": "stored_summary_missing"},
  "combined": {"state": "missing", "reason": "combined_components_unavailable"},
  "formats": {
    "transcript": ["txt", "md", "csv", "xlsx", "json", "srt"],
    "summary": ["txt", "md", "xlsx", "json"],
    "combined": ["txt", "md", "xlsx", "json"]
  },
  "defaults": {
    "include_speaker_labels": true,
    "include_timestamps": true,
    "include_evidence": true
  },
  "language": "ru",
  "duration_seconds": 3661
}
```

The response contains no transcript/summary text, raw source ids, signed URLs,
storage keys, provider ids, credentials, or direct download URL.

States are `available`, `processing`, `partial`, `missing`, `denied`,
`deletion_in_progress`, `failed`, or `audit_unavailable`. A reason is a stable
safe code; localized user copy is rendered by the cabinet.

## File endpoint

`POST /api/v1/cabinet/meetings/{meeting_id}/content-exports`

Request:

```json
{
  "content_scope": "transcript",
  "format": "md",
  "processing_result_id": "uuid",
  "outcome_set_id": null,
  "include_speaker_labels": true,
  "include_timestamps": true,
  "include_evidence": false
}
```

Successful response is the selected attachment, not JSON. Required headers:

- allowlisted `Content-Type`;
- safe UTF-8 `Content-Disposition` filename with ASCII fallback;
- exact `Content-Length`;
- `X-Content-Type-Options: nosniff`;
- private/no-store cache policy.

The response must not include a storage URL/key or provider identifier. Bytes
are released only after the metadata-only completion audit persists.

## Format and scope compatibility

| Scope | TXT | MD | CSV | XLSX | JSON | SRT |
|---|---:|---:|---:|---:|---:|---:|
| transcript | yes | yes | yes | yes | yes | yes |
| summary | yes | yes | no | yes | yes | no |
| combined | yes | yes | no | yes | yes | no |

Unsupported combinations return `422 unsupported_export_combination`; unknown
formats/extensions/MIME aliases return `422 unsupported_export_format`.

## Authorization and revision algorithm

For every POST, the server:

1. resolves authenticated workspace/meeting access;
2. rejects active deletion;
3. loads current transcript and summary artifact policy separately;
4. validates selected result belongs to the meeting/workspace and is terminal;
5. validates selected outcome set is current, content-hash pinned, stored, and
   tied to the selected result when summary is requested;
6. builds the frozen snapshot and serializes the allowlisted format;
7. revalidates lifecycle, access, policy, transcript revision, and summary id /
   content hash within the same bounded transaction;
8. persists metadata-only completion audit;
9. returns bytes.

Combined export is its own decision, derived fail-closed from both component
permissions and readiness states. It does not use the broader package-export
policy and adds no third permissive policy switch. A capability response does
not reserve permission or revision state for a later POST.

## Safe problem responses

| HTTP | Code | Meaning |
|---:|---|---|
| 401 | `authentication_required` | No authenticated user/session. |
| 403 | `export_policy_denied` | Current artifact policy changed during generation. |
| 404 | `meeting_not_found` | Missing or inaccessible meeting; do not reveal which. |
| 409 | `export_unavailable` | Policy/readiness state currently blocks this selection. |
| 409 | `export_revision_stale` | Selected result/outcome is no longer current/exportable. |
| 409 | `meeting_deletion_active` | Deletion blocks content egress. |
| 422 | `unsupported_export_format` | Format is not allowlisted. |
| 422 | `unsupported_export_combination` | Scope cannot be represented by format. |
| 503 | `export_generation_failed` | Snapshot construction or serialization failed; no bytes returned. |
| 503 | `audit_unavailable` | Fail closed because audit evidence could not persist. |

Details never include meeting content, raw ids from inaccessible resources,
paths, storage keys, signed URLs, provider payloads, or stack traces.

## Audit contract

Allowed event types include requested/denied/completed/failed for canonical
content export. Allowlisted metadata is limited to:

- `content_scope`, `format`;
- selected processing result and outcome-set ids plus a one-way revision fingerprint;
- schema/turn-policy/renderer versions;
- access/policy reason, outcome, byte length;
- existing actor, meeting, workspace, device, and timestamp columns.

No content, speaker display name, source reference, private path, provider job,
credential, or signed URL is accepted by the audit metadata sanitizer.

## Browser meeting-detail contract

- One contextual `Экспорт` action opens the existing accessible dialog/sheet
  pattern; Files/governance shows availability but does not duplicate format
  actions.
- Content scope is first. Compatible format groups and safe defaults follow.
- The default dialog view displays scope, compatible format, included options,
  and one concise structural outcome. Selected revisions, readiness, language,
  duration, and response-only lifecycle truth remain available under one
  collapsed `Технические детали` disclosure.
- Submit enters a live announced preparing state and prevents duplicate submit.
  Success closes/returns focus after download begins. Failure retains selection,
  announces a safe reason, and offers retry when appropriate.
- In the embedded macOS client, the generated attachment enters the native
  WebKit download path and opens `NSSavePanel` with the server-suggested
  filename and extension. The reviewer may rename it, choose a writable
  destination, accept normal overwrite confirmation, or cancel. Cancellation
  writes no file, is not reported as generation/download failure, and preserves
  the meeting document and current export selection. A `blob:` artifact is
  never classified as a cabinet route.
- Escape/close, focus containment/return, keyboard operation, visible focus,
  reduced motion, no color-only status, Russian localization, browser and
  embedded widths are mandatory.
- Copy transcript/summary reuses the TXT human formatter and the same
  authorized, revision-pinned, audited endpoint; it announces success/failure
  without introducing an unaudited clipboard data path.

## Compatibility

- Existing `/downloads/transcript` raw/plain behavior stays unchanged.
- Existing `/downloads/summary` is not silently promoted from its seed contract;
  canonical summary uses this new endpoint.
- Existing `/exports` and `/exports/{id}/download` remain a manifest workflow and
  must not claim to include content bytes.
- Raw `transcript.segments` stays additive-compatible; canonical export does not
  delete or rewrite it.
