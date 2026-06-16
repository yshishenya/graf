# Feature 017 Evidence: Access, Sharing, And Downloads

Date: 2026-06-16

Feature: `017-access-sharing-downloads`

## Scope

This evidence covers the implementation of browser/server-owned meeting access,
login-required sharing, server-mediated downloads, safe export packages,
metadata-only activity, and responsive cabinet UI states.

Out of scope for this evidence: public links, external-recipient invitations,
retention execution, deletion execution, admin policy editing, billing, and
desktop-owned egress policy.

## Sanitized Screenshots

All screenshots use synthetic meeting data and are stored under
`specs/017-access-sharing-downloads/evidence/`.

- `017-cabinet-list-desktop.png`: desktop meeting list with access state and
  compact action affordances.
- `017-cabinet-detail-desktop.png`: desktop meeting detail with access,
  sharing, artifact egress, governance, activity, and playback rails.
- `017-cabinet-detail-mobile.png`: compact-width meeting detail with the same
  governance controls stacked without overlap.

Supporting static HTML:

- `017-cabinet-list-current.html`
- `017-cabinet-detail-current.html`

## Visual Smoke

Command:

```sh
NODE_PATH=<bundled-node-modules> <bundled-node> <playwright-screenshot-script>
```

Result:

```text
listDesktop.horizontalOverflow=false
detailDesktop.horizontalOverflow=false
detailDesktop.playbackOverlapsRightPanel=false
detailMobile.horizontalOverflow=false
detailMobile.playbackPosition=static
detailMobile.playbackOverlapsRightPanel=false
clippedButtons=[]
```

## Focused Validation

Command:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_access_sharing_downloads_contract.py \
  tests/contract/test_access_sharing_no_secret_egress.py \
  tests/unit/test_meeting_access_decisions.py \
  tests/unit/test_artifact_egress_view_models.py \
  tests/unit/test_artifact_egress_audit.py \
  tests/integration/test_meeting_access_policy.py \
  tests/integration/test_meeting_share_links.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_cabinet_web_access_states.py
```

Result:

```text
19 passed
```

## Full Local Gate

Command:

```sh
./infra/scripts/ci-local.sh
```

Result:

```text
server_tests=379 passed, 4 skipped
server_lint=pass
python_compile=pass
deployment_evidence_scan=pass
ci_local_result=pass
```

## Secret And Private-Content Review

Reviewed tracked evidence and implementation outputs for:

- real email addresses;
- transcript text from private meetings;
- raw audio;
- credentials, bearer tokens, API keys, passwords;
- signed URLs;
- object-storage keys;
- local filesystem paths;
- raw MediaScribe identifiers.

Result:

```text
forbidden_content_review=pass
evidence_source=synthetic
```
