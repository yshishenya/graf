# Contract: Meeting-owner audio download

## Scope

This feature changes the effective policy used by the existing cabinet artifact
egress contract. It does not add an endpoint or change the response schema.

## Existing routes

- Web and embedded detail pages: `/meetings/{meeting_id}` and
  `/desktop/meetings/{meeting_id}`.
- Server-mediated download:
  `/api/v1/cabinet/meetings/{meeting_id}/downloads/audio`.

Both detail routes use the same `ArtifactEgressState` and the download route
recomputes it after the current access/deletion checks.

## Effective policy matrix

| Viewer | Source/value | Ready validated playback artifact | Expected result |
|---|---|---:|---|
| Meeting owner | missing/default or `workspace_default` + `disabled` | yes | `available`; existing download link; HTTP 200 through server mediation |
| Permitted non-owner | same implicit default | yes | `owner_only`; no link; HTTP 409 with no audio bytes |
| Meeting owner | `meeting_override` + `disabled` | yes | `policy_blocked`; no link; HTTP 409 with no audio bytes |
| Any permitted viewer | accepted `owner_only` | yes | Existing owner-only behavior |
| Any permitted viewer | accepted `allowed` | yes | Existing allowed behavior |
| Any viewer | any accepted policy | no | Existing missing/unavailable bounded result |
| Any viewer | unknown source/value or invalid access/lifecycle | any | Fail closed; no audio bytes |

## Browser and embedded parity

The owner sees the existing `Скачать аудио…` action in both shells when the
shared state is `available`. The action remains a relative server route; neither
surface receives a storage URL, signed URL, object key, credential, or local
filesystem path. A canceled save panel does not change persisted policy or
meeting state and can be retried through the same link.

## Audit contract

The existing metadata-only events and safe reasons remain authoritative:

- allowed request: `download_requested` with `policy_allowed`;
- prepared audio: `download_stream_prepared` with bounded byte length and
  `source_mode=stored_review_m4a`;
- denied request: `download_denied` with a bounded policy/lifecycle/artifact
  reason.

No event or response may contain raw audio, transcript text, storage keys,
signed URLs, credentials, private paths, or private meeting content.

## Compatibility

Transcript, summary, package, playback, public/share, admin-file, auth,
deletion, and storage contracts are unchanged. The existing OpenAPI
`ArtifactEgressState` schema remains valid.
