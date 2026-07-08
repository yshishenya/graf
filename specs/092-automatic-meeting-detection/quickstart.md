# 092 Quickstart: Automatic Meeting Detection

**Date**: 2026-07-08

This quickstart is the validation guide for implementation. It does not approve
production telemetry rollout or production deploy.

## Prerequisites

- Local server dependencies installed for `apps/server`.
- macOS SwiftPM/XCTest environment available for `apps/macos`.
- No real meeting audio, transcript, private calendar content, raw unified-log
  lines, credentials, tokens, signed URLs, passcodes, or private URLs committed
  to tests/evidence.

## Server Validation

Run focused server tests after implementation:

```sh
cd apps/server
pytest \
  tests/contract/test_meeting_detection_api_contract.py \
  tests/contract/test_meeting_detection_admin_contract.py \
  tests/contract/test_meeting_detection_no_secret_content.py \
  tests/integration/test_meeting_detection_migrations.py \
  tests/integration/test_meeting_detection_registry.py \
  tests/integration/test_meeting_detection_telemetry.py \
  tests/integration/test_meeting_detection_admin_review.py \
  tests/unit/test_meeting_detection_candidates.py \
  tests/unit/test_meeting_detection_registry.py \
  tests/unit/test_meeting_detection_redaction.py
```

Expected:

- telemetry endpoint accepts schema-valid metadata-only payloads;
- idempotent duplicate returns existing result;
- same idempotency key with different payload returns conflict;
- forbidden-content payload is rejected before persistence;
- low-score unknown app identity is rejected;
- known target rollups aggregate by target/version/day;
- VKS candidate appears in admin review after passing score/filter;
- non-target admin action suppresses future candidates;
- diagnostic-only draft cannot become prompt-enabled without QA path;
- published registry fetch returns ETag and valid JSON registry.

## Admin UI Validation

Run focused admin tests:

```sh
cd apps/server
pytest \
  tests/contract/test_admin_no_secret_content_egress.py \
  tests/contract/test_admin_csrf_contract.py \
  tests/integration/test_admin_workspace_access.py \
  tests/integration/test_meeting_detection_admin_review.py
```

Manual local browser check:

1. Start local server with seeded workspace/admin session.
2. Submit synthetic telemetry for:
   - known Zoom target;
   - known Yandex Telemost target;
   - unknown high-score VKS candidate;
   - unknown low-score app;
   - known non-target audio utility.
3. Open `/admin/meeting-detection`.
4. Confirm only the high-score unknown candidate appears in the VKS candidate
   queue.
5. Mark one candidate non-target and confirm a non-target rule appears in the
   next registry draft.
6. Add one candidate as `diagnostic_only` and publish registry.
7. Confirm the registry endpoint returns the new entry only as `diagnostic_only`.

Forbidden:

- raw unified-log lines;
- raw meeting URLs or passcodes;
- attendee emails;
- transcript or audio content;
- full local app paths.

## macOS Registry/Telemetry Validation

Run focused Swift tests after implementation:

```sh
cd apps/macos
swift test \
  --filter AppControlAccessibilityTests \
  --filter BrowserTargetEvidenceTests \
  --filter CaptureControlTests \
  --filter DesktopCabinetRoutePolicyTests \
  --filter DesktopCalendarReminderTests \
  --filter MeetingTargetRegistryTests \
  --filter MeetingDetectionCandidateFilterTests \
  --filter MeetingDetectionTelemetryTests \
  --filter MacOSAudioOwnershipParserTests \
  --filter MeetingDetectionPolicyTests \
  --filter SystemAudioPermissionUXTests
```

Expected:

- remote registry cache loads when valid;
- malformed cache quarantines and falls back to previous good cache or packaged
  seed;
- remote registry cannot enable behavior that compiled safety gates disallow;
- low-score unknown apps remain local/redacted;
- browser/Krisp/audio utility/system-service candidates are suppressed before
  upload;
- high-score VKS-like unknown app produces `server_candidate_upload` payload with
  score and reason codes only;
- uploader respects one daily upload plus one immediate high-score candidate
  upload/day, backoff, and local retention.
- settings/health surfaces can disable detection, switch detect-only, expose
  degraded detector state, and revoke target-scoped auto-record preferences
  without hiding manual recording controls.

## macOS Detector Fixture Validation

Use synthetic `AudioHAL` ownership fixtures as the primary native-app detector
input:

- Zoom start: stable `AudioHAL` ownership for `us.zoom.xos`;
- Zoom end: ownership inactive/removal event and end grace passes;
- Yandex Telemost start/end: `AudioHAL` ownership for
  `ru.yandex.desktop.telemost`;
- Krisp/audio utility ownership: suppressed;
- browser ownership: suppressed for native detector;
- unknown high-score candidate: local discovery and upload-eligible rollup;
- unknown low-score candidate: local aggregate only;
- parser malformed line: health-degraded evidence, no prompt.

Expected:

- 5 second stable start debounce before prompt eligibility;
- sub-5-second observations become `target_short_test` telemetry;
- 15 second end grace before candidate end;
- detector failure falls back to manual recording with health evidence;
- unknown apps never produce prompt/recording events.

## Prompt/Auto-Record Validation

After server/admin and detector foundations pass:

1. Start a verified Zoom or Yandex Telemost meeting candidate.
2. Confirm local prompt names the safe target label and capture mode.
3. Confirm Record starts only through existing local prerequisite gate.
4. Confirm persistent local recording state and one-action Stop are visible.
5. Check "always record meetings from this app/service" for one target.
6. Start a later meeting from the same target and confirm auto-record starts only
   after hard gates.
7. Start a different target and confirm the preference is not reused.
8. Revoke the target-scoped preference in settings and confirm future meetings
   prompt or stay manual according to policy.

## Resource Validation

Run local measurement after macOS detector implementation:

- idle detector p95 CPU below 1% over 10 minutes;
- monitoring p95 CPU below 2%;
- additional steady-state RSS below 30 MB;
- telemetry rollup writes below 256 KB/day before upload;
- one registry fetch/day, one telemetry upload/day, and at most one immediate
  high-score candidate upload/day;
- no network upload during active recording unless explicitly required by policy.

## Final Gate

Before closeout:

```sh
infra/scripts/ci-local.sh
```

Record:

- selected risk/validation lane: high-risk product area;
- focused test outputs;
- quickstart scenario outcomes;
- forbidden-content scan result;
- known limitations and deferred targets;
- no production deploy evidence unless a separate release/deploy lane is opened.

## Implementation Evidence - 2026-07-08

Selected lane: high-risk Spec Kit implementation. The slice touches capture
decisioning, desktop settings, telemetry, admin review, registry publishing,
RLS-covered backend tables, diagnostics, and browser/calendar detection
foundations.

Focused validation completed:

- Server/admin quickstart command:
  `.venv/bin/pytest tests/contract/test_meeting_detection_api_contract.py tests/contract/test_meeting_detection_admin_contract.py tests/contract/test_meeting_detection_no_secret_content.py tests/integration/test_meeting_detection_migrations.py tests/integration/test_meeting_detection_registry.py tests/integration/test_meeting_detection_telemetry.py tests/integration/test_meeting_detection_admin_review.py tests/unit/test_meeting_detection_candidates.py tests/unit/test_meeting_detection_registry.py tests/unit/test_meeting_detection_redaction.py`
  passed `48 passed, 1 warning`.
- macOS quickstart command:
  `swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|BrowserTargetEvidenceTests|CaptureControlTests|DesktopCabinetRoutePolicyTests|DesktopCalendarReminderTests|MeetingTargetRegistryTests|MeetingDetectionCandidateFilterTests|MeetingDetectionTelemetryTests|MacOSAudioOwnershipParserTests|MeetingDetectionPolicyTests|SystemAudioPermissionUXTests'`
  passed `124 tests, 0 failures`.
- Focused RLS/admin regression after the first full-CI failure:
  `PYTHONPATH=src uv run --extra dev pytest tests/contract/test_rls_policy_matrix_contract.py tests/unit/test_admin_overview_view_models.py`
  passed `7 passed, 1 warning`.
- Full local gate: `infra/scripts/ci-local.sh` passed with
  `1136 passed, 4 skipped, 1 warning`; server lint passed; python compile
  passed; production compose config rendered; deployment evidence scan passed.
  The RLS live-enforcement substep remained `blocked` only for the expected
  local boundary `postgres_test_database_required`.

Review remediation completed after the critical review:

- macOS packaged seed registry now loads through SwiftPM resources with checkout
  fallback for local tests.
- The runtime path now wires macOS unified-log `AudioHAL` app ownership into the
  detector, prompt, target-scoped auto-record, and local settings/revoke
  controls.
- Parser fixtures cover real `AudioHAL` ownership assertions and inactive/removal
  events; detector end grace is 15 seconds and unknown short-duration
  observations can be re-evaluated instead of being lost.
- Browser targets are forced to require both browser metadata and
  calendar/join intent, while native browser audio ownership is suppressed for
  Yandex Browser, Opera, and generic browser bundles.
- Server registry/admin fixes reject unsafe browser targets, reject candidate
  merges into unknown target ids, add uniqueness constraints for candidates and
  non-target rules, avoid stale workspace draft publishes, and honor server
  `next_upload_after` backoff on desktop telemetry upload.

Forbidden-content scan:

- Source scan covered meeting-detection server modules, API/admin routes,
  macOS meeting-detection sources, and diagnostic bundle/redaction sources.
- The broad pass only matched denylist/redactor literals and unsafe-metadata
  guard terms.
- The narrowed pass found no raw meeting URLs, attendee emails, passcodes,
  token payloads, transcripts, raw audio keys, or private local paths in feature
  source. Remaining matches were expected guard literals: denylist/redactor
  terms, token/display-name reason enum names, `transcriptionGate` metadata
  status fields, and the `/Users/` path detector regex in the server redactor.

Scenario outcomes:

- Native app detector foundation is covered by synthetic `AudioHAL` fixtures for
  Zoom, Yandex Telemost, browser ownership suppression,
  Krisp/audio-utility suppression, malformed lines, debounce, and end grace.
- Browser foundation is covered by metadata-only fixtures: Telemost/Meet joined
  pages with calendar/join intent can classify to safe service-family evidence;
  landing/new/join/settings/device-test/media/voice-search and missing metadata
  fail closed to detect-only/manual-only.
- Calendar/join-intent hints normalize service family from safe meeting hosts
  and do not persist raw URLs, titles, attendees, passcodes, or credentials.
- Admin review, non-target actions, diagnostic-only drafts, registry publishing,
  ETag registry fetch, idempotent telemetry, and unsafe payload rejection are
  covered by focused server tests.

Known limitations and deferred targets:

- No production deploy, release, or live production telemetry rollout was
  performed in this lane.
- Manual local browser/admin smoke from the quickstart was not run; current
  evidence is automated synthetic integration/unit coverage.
- Resource validation targets such as 10-minute CPU/RSS measurement were not
  measured in this turn.
- Browser extension support remains a future adapter option; this slice only
  lays the browser metadata plus calendar/join-intent foundation.
- Prompt-capable first native targets are limited to locally verified Zoom and
  Yandex Telemost. Other native and browser targets remain diagnostic-only,
  detect-only, manual-only, or blocked until separate live validation promotes
  them.

Task and tracker reconciliation:

- `tasks.md` is the local implementation source of truth and has T001-T075
  reconciled as complete after validation.
- GitHub issues `#2727` through `#2801` were created for T001-T075. They were
  not closed in this turn because no commit, PR, merge, release, or deploy was
  requested or performed.
