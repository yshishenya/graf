# Research: Скачивание аудио владельцем по умолчанию

**Feature**: `131-owner-audio-download`
**Date**: 2026-07-26

## Current production behavior

Metadata-only runtime diagnostics showed that the click reaches
`/api/v1/cabinet/meetings/{meeting_id}/downloads/audio`, but the server returns
`409`. Recent audit events contained `download_denied` with the safe reason
`Workspace policy disables this artifact egress`; the associated policy source
was `workspace_default` and the stored value was `disabled`.

The embedded WebKit surface can therefore look inert even though the request
was rejected. The bug is policy resolution, not a missing browser click handler
or an unavailable download endpoint.

## Existing flow

1. Meeting detail rendering calls `artifact_egress_states()` in
   `apps/server/src/twobrain_rec_server/cabinet/egress.py`.
2. The direct audio route calls `download_artifact()`, which re-checks access,
   deletion, policy, and the validated stored playback artifact by calling the
   same `artifact_egress_states()` helper.
3. `resolve_artifact_policy()` returns a persisted policy or an in-memory
   `meeting_default` object with all artifact egress disabled.
4. `_audio_state()` delegates policy and access decisions to
   `_policy_blocked_state()`. A `disabled` value currently blocks every viewer,
   including the meeting owner.
5. The detail template exposes the existing relative download link only when
   the shared audio state is `available`; browser and embedded macOS therefore
   already share the route and response contract.

## Decision

Resolve only an implicit audio `disabled` value to effective `owner_only` at
the shared egress boundary. Treat `meeting_default` and `workspace_default` as
implicit sources. A deliberate per-meeting privacy decision is represented by
`policy_source=meeting_override` and is not promoted. `test_fixture` and unknown
sources remain conservative and blocked unless their value is already
`allowed` or `owner_only`.

This preserves the existing authorization check: an owner gets the action,
while a permitted non-owner still receives the existing owner-only denial.

## Alternatives considered

| Alternative | Decision | Reason |
|---|---|---|
| Change the database column/server default to `allowed` | Reject | Would broaden egress to permitted non-owners and make policy migration/rollback harder. |
| Add a new owner-only download endpoint or client permission | Reject | Duplicates the existing server-mediated trust boundary and could make browser/embedded behavior diverge. |
| Make only the HTML link visible | Reject | Direct requests would still return `409`; the root cause would remain and the route would be inconsistent. |
| Treat every `disabled` row as owner-only | Reject | Would override explicit privacy decisions and test/unknown sources. |
| Apply one effective audio mapping before `_audio_state()` | Choose | Smallest shared change; both UI and direct route inherit the same fail-closed decision. |

## Compatibility notes

Feature `048` intentionally separated review playback from audio download. This
feature supersedes only the former owner download default: playback remains a
separate capability and no playback route or storage behavior changes.

The existing `MeetingArtifactPolicy` column is a string, so accepting the
`meeting_override` source requires no migration. No writer or admin UI is added
in this slice; any explicit per-meeting deny writer must preserve that source
when it is introduced or updated.

## Safety boundaries

- Access, membership, share capability, lifecycle/deletion, validated M4A, and
  storage-size checks remain in the existing route.
- Unknown source/value combinations fail closed.
- Audit metadata remains filtered by `safe_audit_metadata()`.
- Tests and evidence use synthetic bytes/statuses only; no meeting content,
  storage keys, signed URLs, credentials, or private paths are recorded.
