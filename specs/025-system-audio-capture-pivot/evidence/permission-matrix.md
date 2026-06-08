# Permission Matrix

Feature: `025-system-audio-capture-pivot`

This matrix records expected permission outcomes. It is metadata-only: do not
paste raw audio, transcripts, meeting content, credentials, tokens, signed URLs,
or personal contact details.

| Microphone | Screen/System Audio | Normal Recording Outcome | Visible Copy | Manifest Outcome | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| granted | granted | accepted start allowed | no permission blocker | eligible for `saved` if tracks are complete and aligned | not-tested | Manual permission run pending |
| denied | granted | blocked before accepted start | microphone access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| granted | denied/restricted/unknown | blocked before accepted start | Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| denied | denied/restricted/unknown | blocked before accepted start | Microphone and Screen/System Audio access required | `permission_denied` if explicit degraded attempt is recorded | not-tested | Manual permission run pending |
| permission revoked while recording | any required permission missing | stop/finalize as degraded or failed, not saved | permission changed/retry copy required | `permission_denied` or specific capture failure reason | not-tested | Manual permission run pending |

Blocked, failed, degraded, and not-tested rows are not acceptance.
