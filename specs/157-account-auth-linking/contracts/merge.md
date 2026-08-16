# Contract: merge preview and confirmation

## Preview

The preview is read-only and contains only bounded metadata:

- two masked sign-in method descriptions;
- counts of meetings/recordings/artifacts per source workspace;
- workspace names and roles visible to the authenticated principals;
- non-sensitive flags for calendar, active billing, deletion and role blockers;
- deterministic `preview_fingerprint` and policy version;
- explicit list of preserved, unchanged and blocked entity classes.

No transcript, recording URL, provider subject, secret, code or token is
returned.

## Confirm

Confirmation must include:

- the single-use merge intent ID;
- the preview fingerprint and policy version;
- explicit survivor selection;
- CSRF protection and a fresh authentication/proof check;
- an idempotency key bound to the intent.

The server re-runs preflight under row locks. If any source row, proof, policy
version or blocker changed, it returns `merge_preview_stale` or
`merge_blocked` without a partial mutation.

## Success and retry

Success returns only the survivor and a safe result summary. A replay of a
completed idempotency key returns the same summary; a replay of a cancelled,
expired or failed intent performs no write.
