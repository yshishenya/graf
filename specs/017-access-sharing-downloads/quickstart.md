# Quickstart: Access, Sharing, And Downloads

Feature: `017-access-sharing-downloads`
Date: 2026-06-16

This guide defines validation scenarios for the implementation phase. Commands
may be refined in `tasks.md` once exact test files are created.

## Prerequisites

- Current branch: `017-access-sharing-downloads`.
- Feature 016 cabinet routes available.
- Local development dependencies installed for `apps/server`.
- Synthetic meeting fixtures only; do not use private meeting content in
  tracked screenshots or logs.

## 1. Contract And Unit Validation

Run focused tests for the access/egress slice:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/contract/test_access_sharing_downloads_contract.py \
  apps/server/tests/contract/test_access_sharing_no_secret_egress.py \
  apps/server/tests/unit/test_meeting_access_decisions.py \
  apps/server/tests/unit/test_artifact_egress_view_models.py \
  apps/server/tests/unit/test_artifact_egress_audit.py
```

Expected outcome:

- contract schemas accept owner/team/shared/denied states;
- no response model exposes storage keys, signed URLs, credentials, local paths,
  bearer tokens, or raw dependency identifiers;
- audit write failure produces fail-closed share/download/export outcomes.

## 2. Access Policy Validation

Run integration tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_meeting_access_policy.py \
  apps/server/tests/integration/test_meeting_share_links.py
```

Expected outcome:

- owner sees owned meeting in list and detail;
- team member sees team-visible meeting with team state;
- explicitly shared user sees shared meeting;
- unrelated user does not see the row and receives a bounded denied/not-found
  detail response;
- revoked user loses access after one refresh/retry;
- unauthenticated share-link open requires authentication before content.

## 3. Artifact Egress Validation

Run integration tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_artifact_egress_policy.py
```

Expected outcome:

- transcript allowed and audio disabled states render separately;
- direct artifact requests re-check current authorization and policy;
- denied requests expose no storage keys, signed URLs, raw paths, or private
  content;
- missing/processing/failed/deleted artifacts produce safe unavailable states;
- successful download/export writes metadata-only audit evidence;
- audit persistence failure blocks share/revoke/download/export.

## 4. Web UI Validation

Run web-shell tests:

```sh
uv run --extra dev pytest -q \
  apps/server/tests/integration/test_cabinet_web_access_states.py
```

Expected outcome:

- list rows show Owner/Team/Shared access state only for authorized meetings;
- detail page includes share/download/export controls where allowed;
- share modal/drawer shows login-required copy and public links disabled by
  default;
- metadata-only activity trail shows share/revoke/denied/download/export event
  classes without private content;
- download/export unavailable states fit compact embedded layout;
- denied pages do not expose private title, transcript, summary, participant,
  storage, or artifact details.

## 5. Browser Screenshot Evidence

After implementation, start the local server using the existing project run
path documented for server validation, then capture sanitized screenshots for:

- desktop-width meeting list with owner/team/shared rows;
- desktop-width detail share panel;
- desktop-width download/export panel;
- revoked/denied state;
- compact/mobile-width list and detail states;
- embedded desktop route at `/desktop/meetings`.

Expected outcome:

- screenshots use synthetic data;
- no real email addresses, private transcripts, tokens, object keys, signed
  URLs, local paths, or dependency identifiers appear;
- controls match the clean-room 2brain Rec cabinet style from 016 and do not
  copy Krisp assets/copy/visual treatment.

## 6. Full Local Gate

Before closing implementation:

```sh
./infra/scripts/ci-local.sh
```

Expected outcome:

- lint passes;
- server tests pass;
- production compose/config checks pass;
- evidence scan passes;
- no unrelated Spec Kit/local generated noise is included in the feature diff.
