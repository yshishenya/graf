# Quickstart: Cabinet Runtime Truth

## Prerequisites

- Work from branch `047-cabinet-runtime-truth`.
- Confirm active feature:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/047-cabinet-runtime-truth \
  bash .specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

## Focused macOS Validation

Run cabinet state and shell presentation tests:

```sh
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --filter DesktopCabinetConfigurationTests
swift test --package-path apps/macos --filter AppControlAccessibilityTests
```

Expected outcome:

- configured cabinet in loading state is neutral, not green;
- offline and timeout states show server unavailable;
- login/sign-up finished routes map to auth required, not ready;
- active recording safety invariant remains true for every cabinet state.

## Full macOS Gate

```sh
swift test --package-path apps/macos
```

Expected outcome: all macOS tests pass.

## Web Cabinet Validation

Run focused server cabinet tests that cover review state, web shell rendering,
playback/timestamp surfaces, and no-secret/no-content egress:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_cabinet_playback_contract.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected outcome:

- ready, processing, failed, blocked, and unavailable states remain truthful;
- web and desktop-embedded routes use the same review truth;
- no storage URL, object key, signed URL, credential, private path, raw audio,
  transcript text, or private content appears in status/evidence payloads.

## Browser Runtime Check

If server UI files changed or if release confidence requires a visual check,
run a fixture-backed browser check for:

- web ready desktop viewport;
- desktop embedded ready viewport;
- mobile-width viewport;
- processing, failed, no-audio, deleting, policy-disabled, and auth-required
  unavailable states;
- no horizontal overflow or text overlap;
- Russian-first visible copy.

Record only metadata-safe evidence in
`specs/047-cabinet-runtime-truth/evidence/validation-log.md`.

## Production Health Truth Check

Check current production health separately from desktop runtime state:

```sh
curl -fsS --max-time 5 https://rec.2brain.pro/api/v1/health/live
curl -fsS --max-time 5 https://rec.2brain.pro/api/v1/health/ready
```

Expected outcome: report the real current server state; do not use this as
proof that the installed desktop shell is ready unless the desktop app also
observes a ready cabinet route.

## Full Local Gate

Before PR or release readiness:

```sh
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```
