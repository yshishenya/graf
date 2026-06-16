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

## Production Smoke

Command:

```sh
./infra/scripts/cd-remote.sh --execute --branch 017-access-sharing-downloads
```

Follow-up read-only verification:

```sh
ssh 2brain.dev 'cd /opt/projects/2brain-rec && git rev-parse HEAD'
ssh 2brain.dev 'cd /opt/projects/2brain-rec && docker compose -f infra/docker-compose.yml ps'
ssh 2brain.dev 'cd /opt/projects/2brain-rec && docker compose -f infra/docker-compose.yml exec -T rec-api alembic current'
curl -fsS https://rec.2brain.pro/api/v1/health/live
curl -fsS https://rec.2brain.pro/api/v1/health/ready
```

Result:

```text
deployed_sha=39b8c5fbfae74159e5e50f5c2471f19ff64f1e36
remote_branch=master
rec_api_status=healthy
alembic_current=0006_access_sharing_downloads
health_live={"status":"ok"}
health_ready={"status":"ready"}
readiness_verdict=infra_smoke_ready
```

## Secret And Private-Content Review

Reviewed tracked evidence and implementation outputs for:

- real email addresses;
- private transcript payloads;
- audio payloads;
- credentials, auth headers, access credentials, passwords;
- presigned storage links;
- object-storage identifiers;
- local filesystem paths;
- raw MediaScribe identifiers.

Result:

```text
forbidden_content_review=pass
evidence_source=synthetic
```
