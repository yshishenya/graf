# Evidence: 036 Owner Review Live Polish

Feature: `036-owner-review-live-polish`

This directory stores metadata-safe evidence for the owner review, notes/action
truth, runtime UI polish, and readiness-claim slice after feature 035.

## Evidence Boundary

Allowed evidence:

- safe route/status observations for `https://rec.2brain.pro`;
- temporary smoke-session result classes and cleanup result classes;
- metadata-only owner review list/detail/governance proof;
- synthetic or fully sanitized desktop/web screenshots;
- installed `/Applications/2brain Rec.app` runtime path proof;
- readiness reports, launch gaps, validation logs, and clean-room comparison
  notes.

Forbidden evidence:

- raw audio;
- private transcript text or generated private meeting content;
- private meeting titles when they identify a real meeting;
- private emails, account identifiers, cookies, credentials, bearer/session
  tokens, signed URLs, provider payloads, or secret local paths;
- private Krisp/reference screenshots or copied brand assets.

## Current Baseline

Feature 035 left the strongest truthful claim at `pilot_blocked` with bounded
`infra_smoke_ready`. Feature 036 closes the owner review and installed-app
walkthrough evidence without broadening the rollout claim. The remaining 036
readiness blockers are:

- `notes-action-output`;
- `production-user-rollout-evidence`;
- P2 browser target and signed-installer evidence.

The initial Chrome/live observation on 2026-06-16 showed
`https://rec.2brain.pro/meetings` returning `401 missing_auth_context` without a
browser-safe owner session. The approved Chrome owner session on 2026-06-22 then
proved the production owner list, one detail route, and governance/access panel
metadata-safely without committing private meeting content.

## Owner Review Execute Mode

Use execute mode only with a temporary owner-review session token approved for
validation. Keep the token outside the repository, never paste it into evidence,
and delete the token file after the run.

```sh
tmp_token_file="$(mktemp)"
chmod 600 "$tmp_token_file"
# Write the temporary session token into "$tmp_token_file" through a safe local
# operator flow. Do not echo it in shell history.
PYTHONPATH=src uv run python scripts/prove_owner_review_live.py \
  --api https://rec.2brain.pro \
  --token-file "$tmp_token_file" \
  --run-id feature-036-owner-review-live \
  --execute
rm -f "$tmp_token_file"
```

The script may report only route/status classes such as `ready`, `empty`,
`blocked`, or `deferred`; it must not print session material, private titles,
transcripts, account identifiers, request headers, or signed URLs.

## Files

- `validation-log.md`: command and manual walkthrough evidence.
- `launch-gap-register.md`: current blocker register carried forward from 035.
- `readiness-report.json`: generated readiness report after implementation.
- `readiness-report.md`: reviewer-facing readiness summary after implementation.
- `clean-room-reference.md`: V8/reference lessons and brand-distance checks.
- `screenshots/`: metadata-safe screenshots or markdown blocker notes only.

## Validation Rule

Do not close feature 036 or any mapped GitHub issue until evidence is recorded
here, the matching task is marked `[X]`, forbidden-content scans are clean, and
the readiness claim is updated without overclaiming.
