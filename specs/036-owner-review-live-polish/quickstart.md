# Quickstart: Owner Review Live Polish

Feature: `036-owner-review-live-polish`

Use this guide to validate 036 end to end. Commands assume repository root.

## 1. Anchor The Feature

```sh
SPECIFY_FEATURE_DIRECTORY=specs/036-owner-review-live-polish \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: the active feature resolves to `036-owner-review-live-polish` and
`tasks.md` is present before implementation validation.

## 2. Focused Server Validation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_web_access_states.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_mvp_loop_readiness_matrix.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_mvp_loop_readiness_contract.py
```

Expected: all selected tests pass; no test snapshot includes private content or
secret-bearing auth material.

## 3. Smoke Owner Session Dry Run

```sh
cd apps/server
PYTHONPATH=src uv run python scripts/issue_smoke_auth_session.py \
  --run-id feature-036-owner-review-dry-run \
  --token-file /tmp/twobrain-rec-036-owner-review-token \
  --ttl-seconds 900
```

Expected: `auth_session_result` is `dry_run`, `token_written` is `false`, and
stdout contains no raw token.

## 4. Production Owner Review Proof

Only run execute mode when production env is configured and the token file path
is outside the repo.

```sh
cd apps/server
RUN_ID="feature-036-owner-review-$(date +%Y%m%d%H%M%S)"
TOKEN_FILE="/tmp/twobrain-rec-${RUN_ID}-token"
PYTHONPATH=src uv run python scripts/issue_smoke_auth_session.py \
  --run-id "$RUN_ID" \
  --token-file "$TOKEN_FILE" \
  --ttl-seconds 900 \
  --execute
```

Then validate `https://rec.2brain.pro` using the approved owner-review proof
path from the implementation tasks. Do not print or commit the token. Store
only sanitized route/state evidence under
`docs/evidence/036-owner-review-live-polish/`.

Cleanup:

```sh
cd apps/server
PYTHONPATH=src uv run python scripts/cleanup_smoke_auth_session.py \
  --run-id "$RUN_ID" \
  --auth-session-id "<non-secret-auth-session-id-from-issuer>" \
  --execute
rm -f "$TOKEN_FILE"
```

Expected: cleanup reports `auth_cleanup_result=pass` or a documented blocker.
No token/cookie/header values appear in committed files.

## 5. Installed Desktop Runtime Proof

Build/stage the app as required by implementation tasks, install to
`/Applications/2brain Rec.app`, then launch the installed bundle:

```sh
open "/Applications/2brain Rec.app"
```

Expected:

- active process path resolves to `/Applications/2brain Rec.app`;
- main workspace is meeting/review-first rather than diagnostics-first;
- native Start/Record, Pause, Resume, and Stop controls remain visible and
  usable in active, paused, resumed, and stopped states;
- screenshots committed under 036 are metadata-safe.

## 6. macOS Build And Focused Tests

```sh
swift build --package-path apps/macos
swift test --package-path apps/macos --filter 'DesktopCabinet|CaptureControl|AppControlAccessibility|MeetingMuteTruth|SystemAudioPermission'
```

Expected: build passes and focused tests prove desktop shell/capture control
states still behave.

## 7. Readiness Evidence Regeneration

```sh
cd apps/server
PYTHONPATH=src uv run python scripts/generate_mvp_loop_readiness.py \
  --feature 036-owner-review-live-polish \
  --output-dir ../../docs/evidence/036-owner-review-live-polish
```

Expected: readiness report, launch gap register, and current product status
agree on the same strongest truthful claim.

## 8. Forbidden-Content Scan

```sh
rg -n --hidden --glob '!*.pyc' \
  'Authorization:|Bearer |X-Auth-Session|session_token|cookie|Set-Cookie|signed_url|presigned|@|/Users/|transcript text|raw audio' \
  specs/036-owner-review-live-polish \
  docs/evidence/036-owner-review-live-polish
```

Expected: no private/secret matches. Policy-only matches are acceptable only
when they describe forbidden evidence and do not contain values.

## 9. Canonical Local Gate

```sh
infra/scripts/ci-local.sh
git diff --check
```

Expected: local CI passes or any bounded expected block is documented; diff
check has no output.
