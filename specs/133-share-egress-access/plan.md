# Implementation Plan: полный egress внешнего приглашения

## Constitution Check

- **Pass — Spec-Driven Delivery**: high-risk auth/privacy/storage work uses
  clarify, checklists, tasks, analyze and focused/full validation.
- **Pass — access boundary**: reuse exact-recipient proof and the existing
  `decide_meeting_access` / egress gates; no bypass or alternate ACL.
- **Pass — deletion truth**: final egress recheck remains in place so revoke and
  deletion win races.
- **Pass — data boundary**: no new external destination, secret, URL or content
  logging is introduced.
- **Pass — product scope**: no capture, desktop, legacy routing or public-link
  change.

## Technical Approach

1. Extend the existing egress recheck helper with an optional
   `ShareRecipientAccessProof` and pass it to `decide_meeting_access`.
2. Return the proof from `_authorized_shared_meeting` and pass it through shared
   playback, artifact download and content-export routes.
3. Carry the proof through both the initial and final checks in content export;
   leave owner/team/admin callers on the default `None` path.
4. Extend the external full-invitation integration test to exercise transcript
   download and actual transcript/combined exports, plus keep revoke checks.
5. Update changelog and quickstart evidence after focused checks; run local CI
   before PR.

## Files To Change

- `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/server/tests/integration/test_recording_share_public_link.py`
- `CHANGELOG.md`
- `specs/133-share-egress-access/quickstart.md`
- `specs/133-share-egress-access/tasks.md`

## Validation And Release Gate

- Focused invitation, playback and export tests first.
- `git diff --check`, compileall and targeted Ruff.
- `infra/scripts/ci-local.sh` before closeout/PR.
- No production mutation in implementation phase. A release requires explicit
  user approval, CalVer preparation, Developer ID/macOS validation and the
  guarded remote dry-run/execute flow.

## Complexity Check

The smallest safe fix is one optional parameter through the existing call
chain. No new abstraction, dependency, endpoint, migration or storage model is
needed.
