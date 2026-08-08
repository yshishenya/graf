# Security Checklist: полный egress внешнего приглашения

- [X] Exact recipient proof remains bound to every downstream access recheck.
- [X] Grant scope, active status and expiry remain fail-closed.
- [X] Revoke and deletion win races after the page is rendered.
- [X] `summary_only` cannot reach full content routes.
- [X] Artifact policy remains enforced per requested artifact.
- [X] Canonical playback is served only through the existing server route.
- [X] Storage URLs, keys, signed URLs, raw uploads and internal metadata are not
  returned.
- [X] Existing audit event path remains the source of egress evidence.
- [X] No secrets or private meeting content enter specs, logs or evidence.
- [X] Owner/team/admin callers retain their existing authorization semantics.
