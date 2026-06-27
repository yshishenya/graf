# Implementation Evidence: Calendar Context Ingestion

**Feature**: 060-calendar-context-ingestion
**Branch**: `codex/060-calendar-context-ingestion`
**Updated**: 2026-06-27

## Risk / Validation Lane

- Lane: High-risk product area.
- Reason: Calendar integration touches provider credentials, sensitive meeting-adjacent calendar content, retention/deletion accounting, API contracts, external provider failure states, and desktop prompts near recording start.
- Implementation boundary: code/test implementation does not deploy by itself. Release/deploy/build evidence belongs to the final closeout stage after PR merge and release gate validation.
- Origin/master sync: pass. `origin/master` (`586691f`) is an ancestor of feature HEAD `bf36517`.

## T001 Evidence Log Setup

- Evidence log created with sections for tests, provider fixtures, privacy scan, RLS proof, desktop proof, and known limitations.
- Active feature anchor checked with `SPECIFY_FEATURE_DIRECTORY=specs/060-calendar-context-ingestion .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`.
- Result: `FEATURE_DIR=/Users/yshishenya/.codex/worktrees/5362/crisp/specs/060-calendar-context-ingestion`; available docs include `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and `tasks.md`.

## T002 Checklist Recheck

- Rechecked `specs/060-calendar-context-ingestion/checklists/calendar-integration.md` after merging the latest `origin/master`.
- Result: CHK001-CHK044 remain satisfied against current `spec.md`, `plan.md`, `research.md`, `provider-deep-dive.md`, `data-model.md`, contracts, `quickstart.md`, and `tasks.md`.
- Placeholder scan over current 060 spec/plan/tasks/checklists found no unresolved `NEEDS CLARIFICATION`, `TODO`, `TKTK`, `???`, or `<placeholder>` markers in active requirements. The only `NEEDS CLARIFICATION` string is a checked checklist assertion.
- Real integration touchpoints from 057/058 master state exist for ingest, processing, cabinet, access/share boundaries, meeting lifecycle, desktop upload, capture UI, app wiring, and shared system-audio models.
- Added `specs/060-calendar-context-ingestion/checklists/pre-implementation-readiness.md` for the post-master-sync requirement-quality pass.

## Speckit Analyze Rerun

- Reran the pre-implementation cross-artifact analysis after merging `origin/master`.
- Inputs: `spec.md`, `plan.md`, `tasks.md`, `.specify/memory/constitution.md`, data model, contracts, quickstart, and current 060 checklists.
- Result: no unresolved critical/high blockers found.
- Coverage: FR-001 through FR-026 and SC-001 through SC-011 have mapped tasks, validation tasks, or explicit no-go boundaries in `tasks.md`.
- Constitution alignment: pass. Calendar credentials stay server-owned, no hidden/automatic recording is introduced in 060, deletion/retention accounting is planned, and high-risk validation gates remain required.

## Tests

- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_provider_fixtures.py`
  - Result: pass, 5 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/integration/test_calendar_persistence.py`
  - First TDD run before implementation: expected fail, missing calendar package/model exports/router.
  - After foundation implementation: pass, 19 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar src/twobrain_rec_server/api/calendar.py src/twobrain_rec_server/db/models/calendar.py src/twobrain_rec_server/db/migrations/versions/0010_calendar_context_ingestion.py tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/integration/test_calendar_persistence.py`
  - Result: pass.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/integration/test_calendar_persistence.py`
  - US1 rerun after service/API implementation: pass, 27 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar src/twobrain_rec_server/api/calendar.py tests/unit/test_calendar_credentials.py tests/contract/test_calendar_context_contract.py tests/integration/test_calendar_persistence.py`
  - Result: pass after import-sort autofix.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_openapi_contract_drift.py tests/contract/test_calendar_context_contract.py`
  - Result after regenerating `specs/012-server-ingest-foundation/contracts/openapi.yaml`: pass, 11 passed, 1 pytest-asyncio deprecation warning.

## US1 Source Management Evidence

- T022 completed: `cryptography` is present in `apps/server/pyproject.toml` and `apps/server/uv.lock`; `apps/server/src/twobrain_rec_server/calendar/credentials.py` seals credentials with Fernet, exposes fingerprint-only metadata, and has no plaintext API response path.
- T040/T044 completed: `GET /api/v1/calendar/providers` returns provider presets for Yandex, Mail.ru, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, VK WorkSpace/custom CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud/SOGo-like CalDAV, and custom CalDAV.
- T041/T045/T047 completed: source connect/list/get/select/sync/disconnect routes use `calendar.service` and tenant-scoped persistence. Missing sources return `calendar_source_not_found`; unsupported providers return `unsupported_calendar_provider` without echoing submitted secret material.
- T042 completed: selected-calendar persistence deduplicates selected provider calendar ids, stores selected calendars, and records a rolling future sync horizon on sync request.
- T043/T046 completed: safe credential failure mapping covers invalid app password, OAuth unavailable, tenant denial, provider timeout, and rate limit without provider secret content.
- T038 completed: runtime FastAPI OpenAPI and committed `specs/012-server-ingest-foundation/contracts/openapi.yaml` match after calendar route registration.
- US1 limitation: live provider calendar discovery is not used in validation. For 060 implementation evidence, discovery results are represented by synthetic selected calendar ids and provider capability presets; live provider checks require separate approval and metadata-only evidence.

## US2 Event Context Evidence

- T051-T057 completed: `apps/server/tests/fixtures/calendar.py` and `apps/server/tests/unit/test_calendar_provider_fixtures.py` cover Yandex CalDAV, Mail.ru CalDAV, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, VK WorkSpace/custom CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV fixtures.
- T058 completed: `apps/server/tests/unit/test_calendar_normalization.py` covers recurrence, all-day events, floating-time input, missing `DTEND`, duplicate `UID` copies, cancelled instances, and moved recurrence instances.
- T059 completed: `apps/server/tests/unit/test_calendar_conference_links.py` covers sensitive description/passcode redaction, multiple links, attachment URL exclusion, and cancelled/stale event link suppression.
- T060/T061 completed: normalization rejects raw provider payload/token extras, parses minimal iCalendar `VEVENT` identity/schedule/recurrence/link fields, and marks private/free-busy limitations without fabricating title/participants.
- T062-T067 completed: provider adapters map native Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, generic iCalendar/CalDAV, and custom CalDAV-style Russian/on-prem provider families into the normalized event contract. Conference-link extraction returns only provider family, URL hash, redacted preview, and passcode presence.
- T068 completed: `apply_calendar_sync_result` upserts event snapshots, participant rows, conference-link rows, source versions, provider deletion markers, and external-calendar sync tokens.
- T069/T070/T107 completed: upcoming calendar event and desktop prompt endpoints shape stored future snapshots into safe API responses.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/integration/test_calendar_persistence.py`
  - US2 rerun after iCalendar/upcoming implementation: pass, 37 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar src/twobrain_rec_server/api/calendar.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/contract/test_calendar_no_secret_content_egress.py tests/integration/test_calendar_persistence.py`
  - Result: pass after import-sort autofix.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_openapi_contract_drift.py tests/contract/test_calendar_context_contract.py`
  - Result after regenerating `specs/012-server-ingest-foundation/contracts/openapi.yaml`: pass, 11 passed, 1 pytest-asyncio deprecation warning.

## US3 Recording-Time Context Evidence

- T072/T074/T076 completed: `apps/server/tests/unit/test_calendar_recording_context.py` and `apps/server/tests/integration/test_calendar_persistence.py` cover single current-event selection, explicit current/future selection, past selected-event rejection, API rejection for past-event-to-later-recording links, ambiguous current-event fallback, and no-context fallback.
- T073/T077/T078 completed: `apps/server/tests/contract/test_calendar_context_contract.py` covers `PUT /api/v1/meetings/{meeting_id}/calendar-context` and `DELETE /api/v1/meetings/{meeting_id}/calendar-context` against the real FastAPI app and sqlite-backed persistence.
- T075/T081 completed: `apps/macos/Shared/Tests/DesktopUploadClientTests.swift` verifies optional `calendarContextEventId` queue persistence and metadata-only calendar context link requests. `DesktopUploadClient` attempts the link after meeting creation and does not store provider credentials on desktop.
- T079/T080 completed: meeting create responses expose `title` and `title_source`; calendar context linking preserves manual titles and applies safe calendar titles only to untitled recordings.
- No retrospective matching evidence: there is no background job or existing-meeting scan in the US3 path; `RecordingCalendarContextLink` is created only by the explicit calendar-context endpoint payload and rejects already-ended events relative to recording start.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_recording_context.py tests/contract/test_calendar_context_contract.py`
  - Result: pass, 10 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar/service.py src/twobrain_rec_server/api/calendar.py tests/unit/test_calendar_recording_context.py tests/contract/test_calendar_context_contract.py`
  - Result: pass after import-sort autofix.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_openapi_contract_drift.py tests/contract/test_calendar_context_contract.py`
  - Result after regenerating `specs/012-server-ingest-foundation/contracts/openapi.yaml`: pass, 12 passed, 1 pytest-asyncio deprecation warning.
- Combined backend focused checkpoint:
  `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/unit/test_calendar_recording_context.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/contract/test_openapi_contract_drift.py tests/integration/test_calendar_persistence.py`
  - Result: pass, 46 passed, 1 pytest-asyncio deprecation warning.

## US5 Privacy, Deletion, Access, And Provider-Failure Evidence

- T093/T098 completed: `apps/server/tests/integration/test_calendar_deletion_lifecycle.py` proves a meeting deletion request accounts for an active calendar context link by marking it unlinked with `meeting_deletion_requested` and recording metadata-only calendar audit state.
- T094/T099 completed: `apps/server/tests/integration/test_calendar_access_policy.py` proves authorized cabinet review can read safe calendar roster context while denied viewers receive no review/roster response.
- T095/T100/T101 completed: `apps/server/tests/integration/test_calendar_provider_failures.py` proves provider timeout moves the source into `stale` with safe error code and does not block ordinary meeting creation. Calendar context link attempts from desktop are best-effort and cannot block upload.
- T096 completed: `apps/server/tests/unit/test_redaction.py` covers calendar-sensitive recursive redaction and forbidden evidence markers for app passwords, raw event payloads, and passcodes.
- T048 completed: `apps/server/tests/unit/test_calendar_credentials.py` verifies calendar provider problem codes map to automatic, metadata-only retry semantics without echoing secrets.
- Focused US5 tests:
  `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_calendar_disconnect_lifecycle.py tests/integration/test_calendar_deletion_lifecycle.py tests/integration/test_calendar_access_policy.py tests/integration/test_calendar_provider_failures.py tests/unit/test_redaction.py tests/unit/test_calendar_credentials.py`
  - Result included in the combined backend checkpoint below.

## US5 Disconnect Lifecycle Evidence

- T029/T049/T092/T097 completed: `apps/server/src/twobrain_rec_server/calendar/lifecycle.py` now marks calendar sources disconnected, purges credential envelopes, marks selected calendars disconnected, and deletes unmatched future snapshots plus participant/conference-link child rows.
- Matched context boundary: disconnect purge excludes snapshots referenced by active `RecordingCalendarContextLink` rows, so already matched context remains under meeting retention/deletion policy.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_calendar_disconnect_lifecycle.py tests/contract/test_calendar_context_contract.py`
  - Result: pass, 8 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar/lifecycle.py tests/integration/test_calendar_disconnect_lifecycle.py`
  - Result: pass.
- Combined backend focused checkpoint after disconnect lifecycle:
  `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/unit/test_calendar_recording_context.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/contract/test_openapi_contract_drift.py tests/integration/test_calendar_persistence.py tests/integration/test_calendar_disconnect_lifecycle.py`
  - Result: pass, 47 passed, 1 pytest-asyncio deprecation warning.

## US4 Roster Boundary Evidence

- T083/T086 completed: `apps/server/tests/unit/test_calendar_participants.py` covers organizer, required attendee, optional attendee, declined attendee, hidden/no-email attendee, resource, room, group, internal, external, and duplicate participant handling.
- T084/T088 completed: `apps/server/tests/contract/test_calendar_context_contract.py` verifies upcoming event responses include `attendee_count`, `roster_state`, and `recipient_candidate_count` without attendee email dumps.
- T085/T090 completed: `apps/server/tests/unit/test_cabinet_view_models.py` proves calendar roster display names do not rename transcript/diarized speaker labels and do not create access/share grant fields.
- T087 completed: `apps/server/src/twobrain_rec_server/calendar/sync.py` persists normalized/deduplicated participants and stores only safe roster aggregate fields in event summaries.
- T089 completed: `apps/server/tests/integration/test_calendar_access_policy.py` proves authorized cabinet review includes `calendar_roster` with safe participant metadata, while raw participant emails are not serialized in the review model.

## US7 Recipient Candidate No-Egress Evidence

- T116/T119 completed: `apps/server/tests/unit/test_calendar_recipient_candidates.py` covers future recipient candidate classes for organizer, internal attendee, optional attendee, declined attendee, room, group, and unavailable/no-email cases.
- T117 completed: `apps/server/tests/contract/test_calendar_no_secret_content_egress.py` verifies recipient candidates do not include send/share/access payloads.
- T118/T121 completed: `apps/server/tests/integration/test_meeting_share_links.py` verifies linking a meeting to a calendar event with an external attendee creates zero `MeetingShareGrant` rows.
- T120 completed: API schemas expose candidate counts and safe roster states without raw attendee dumps.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_participants.py tests/unit/test_calendar_recipient_candidates.py tests/unit/test_cabinet_view_models.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_context_contract.py tests/integration/test_meeting_share_links.py tests/integration/test_calendar_persistence.py`
  - Result: pass, 31 passed, 1 pytest-asyncio deprecation warning.
- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar/normalize.py src/twobrain_rec_server/calendar/sync.py src/twobrain_rec_server/api/calendar.py src/twobrain_rec_server/api/schemas.py tests/unit/test_calendar_participants.py tests/unit/test_calendar_recipient_candidates.py tests/unit/test_cabinet_view_models.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_context_contract.py tests/integration/test_meeting_share_links.py tests/integration/test_calendar_persistence.py`
  - Result: pass after import-sort autofix.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_openapi_contract_drift.py tests/contract/test_calendar_context_contract.py`
  - Result after regenerating `specs/012-server-ingest-foundation/contracts/openapi.yaml`: pass, 12 passed, 1 pytest-asyncio deprecation warning.
- Planned focused gates are listed in `specs/060-calendar-context-ingestion/tasks.md` T127-T133 and `specs/060-calendar-context-ingestion/quickstart.md`.

## Provider Fixtures

- T003/T004/T014 provider fixture foundation completed.
- Fixture guidance: `apps/server/tests/fixtures/calendar/README.md`.
- Fixture module: `apps/server/tests/fixtures/calendar.py`.
- Fixture tests: `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- Provider coverage requirement remains Yandex, Mail.ru, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, VK WorkSpace/custom CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV.

## Privacy Scan

- T005 forbidden-content notes completed at `specs/060-calendar-context-ingestion/validation/forbidden-content-notes.md`.
- Focused forbidden-content scan after fixture setup:
  `rg -n "\\b(refresh_token|app_password|signed_url|attendee_email_dump|raw_event_payload)\\s*[:=]|Authorization\\s*:|Bearer [A-Za-z0-9._~+/-]+|\\bpasscode\\s*[:=]" specs/060-calendar-context-ingestion apps/server/tests/fixtures apps/server/src/twobrain_rec_server apps/macos --glob 'specs/060-calendar-context-ingestion/**' --glob 'apps/server/tests/fixtures/calendar.py' --glob 'apps/server/src/twobrain_rec_server/calendar/**' --glob 'apps/server/src/twobrain_rec_server/api/calendar.py' --glob 'apps/macos/RecApp/Sources/Calendar/**' --glob 'apps/macos/Shared/Sources/Models/CalendarContextModels.swift' --glob '!specs/060-calendar-context-ingestion/quickstart.md' --glob '!specs/060-calendar-context-ingestion/validation/forbidden-content-notes.md'`
  - Result: pass, no matches.
- Focused forbidden-content scan after US1 backend and US6 desktop prompt implementation:
  - Result: pass, no matches. The scan uses word boundaries so safe flag names such as `contains_passcode` are not treated as secret material.
- Focused forbidden-content scan after US2 iCalendar/upcoming implementation:
  - Result: pass, no matches.
- Focused forbidden-content scan after US3-US7 implementation:
  - Result: pass, no matches (`rg` exit code 1).
- Current preparation evidence contains no real provider credentials, live calendar payloads, attendee email dumps, meeting passcodes, signed URLs, screenshots, transcript text, or private meeting content.

## RLS Proof

- T008/T018/T019 RLS inventory and migration policy scaffolding completed for new calendar table names.
- Postgres runtime enforcement proof is still pending T128.

## Desktop Proof

- T103/T108/T110/T111 completed: `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift` covers one-minute join prompt timing, event-start record prompt timing, dismissed prompts, overlapping-current-event fallback, private/unsafe title fallback, endpoint response decoding, and manual-action accessibility copy.
- T104/T112 completed: `apps/macos/Shared/Tests/CaptureControlTests.swift` verifies `CaptureControlView` wires `CalendarPromptView`, separate primary/dismiss actions, and calendar prompt accessibility identifiers.
- T105/T114 completed: `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` verifies calendar prompt accessibility identifiers and Russian copy stating that recording does not start automatically.
- T106/T109 completed: `apps/macos/Shared/Tests/DesktopUploadClientTests.swift` verifies the desktop calendar client uses the read-only `/api/v1/desktop/calendar/upcoming` endpoint.
- T113 completed: `apps/macos/RecApp/App/TwoBrainRecApp.swift` polls desktop upcoming calendar context and clears prompt state on failure with metadata-only `calendar_unavailable` logging.
- `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCalendarReminder`
  - Result after final upload-client context changes: pass, 8 tests, 0 failures.
- `swift test --package-path apps/macos --disable-swift-testing --filter 'CaptureControl|AppControlAccessibility|DesktopUploadClient'`
  - Result after adding calendar prompt UI/accessibility/client regressions and context-link request support: pass, 54 tests, 0 failures.
- No auto-record evidence: `DesktopCalendarReminderService.activePrompt` only returns prompt state; `DesktopCalendarPromptActions.performPrimaryAction` calls `startRecording()` only for an explicit record prompt primary action; active recording suppresses record prompts.
- No auto-join evidence: join prompts only call `NSWorkspace.shared.open(url)` through explicit primary action and do not invoke recording.

## Known Limitations

- 060 remains read-only for calendars: no calendar mutation, no message sending, no share grants from attendees, no bot auto-join, no auto-record, and no retrospective matching of old recordings.
- Live provider checks are not used for implementation evidence unless separately approved; synthetic fixtures are the default proof surface.

## Documentation And Final Focused Validation

- T123 completed: `docs/current-product-status.md` records the 060 local feature-branch status, provider families, validation evidence, and explicit out-of-scope boundaries for auto-record, auto-join, calendar mutation, sending, share grants, attachments, retrospective matching, live provider credentials, PR/release/deploy, and production smoke.
- T124 completed: `CHANGELOG.md` records 060 behavior, privacy/security impact, validation summary, compatibility/known-limitations boundary, final local CI evidence, and pending PR/release/deploy status.
- T125 completed: `quickstart.md` now includes `tests/integration/test_persistent_ingest_storage.py` in the persistence/lifecycle check because meeting create responses expose `title` and `title_source`.
- T126 completed: `provider-deep-dive.md` now records implementation corrections: synthetic metadata-only provider fixtures are the evidence surface; native mappers exist for Google Calendar, Microsoft Graph, Exchange EWS, and Bitrix24; Russian/on-prem providers without verified rich APIs stay on CalDAV/iCalendar capability labels.
- T127-T129 completed through the combined backend focused checkpoint below. The command covered the exact unit, contract, OpenAPI drift, RLS, persistence/lifecycle/access/provider-failure/share, and persistent ingest tests required by the final task set.
- T130-T132 completed through the macOS and forbidden-content focused checkpoints below.

## Focused Final Implementation Checkpoint

- `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar src/twobrain_rec_server/api/problems.py src/twobrain_rec_server/api/schemas.py src/twobrain_rec_server/api/ingest.py src/twobrain_rec_server/cabinet/queries.py src/twobrain_rec_server/cabinet/view_models.py src/twobrain_rec_server/deletion/service.py tests/unit/test_calendar_credentials.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/unit/test_redaction.py tests/integration/test_calendar_persistence.py tests/integration/test_calendar_provider_failures.py tests/integration/test_calendar_access_policy.py tests/integration/test_calendar_deletion_lifecycle.py`
  - Result: pass.
- `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/unit/test_calendar_recording_context.py tests/unit/test_calendar_participants.py tests/unit/test_cabinet_view_models.py tests/unit/test_redaction.py tests/unit/test_calendar_recipient_candidates.py tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/contract/test_openapi_contract_drift.py tests/integration/test_calendar_persistence.py tests/integration/test_calendar_disconnect_lifecycle.py tests/integration/test_calendar_deletion_lifecycle.py tests/integration/test_calendar_access_policy.py tests/integration/test_calendar_provider_failures.py tests/integration/test_meeting_share_links.py tests/integration/test_persistent_ingest_storage.py`
  - Result: pass, 91 passed, 1 pytest-asyncio deprecation warning.
- `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCalendarReminder`
  - Result: pass, 8 tests, 0 failures.
- `swift test --package-path apps/macos --disable-swift-testing --filter 'CaptureControl|AppControlAccessibility|DesktopUploadClient'`
  - Result: pass, 54 tests, 0 failures.
- Forbidden-content scan from `quickstart.md`
  - Result: pass, no matches.

## Full Local CI And Closeout Readiness

- T133 completed after the final Ponytail simplification:
  `infra/scripts/ci-local.sh`
  - Result: pass, `ci_local_result=pass`.
  - Server tests: `771 passed, 4 skipped, 103 warnings`.
  - Server lint: pass.
  - Python compile: pass.
  - RLS validation boundary: expected local boundary output stayed `rls_validation_result=blocked` with `reason=postgres_test_database_required`, and did not fail the CI gate.
  - Production compose config: rendered successfully.
  - Deployment evidence scan: pass.
- T134 Ponytail complexity review:
  - Finding applied: `apps/server/src/twobrain_rec_server/calendar/adapters.py`: `delete/yagni`: unused `CalendarAdapterResult` and one-implementation `CalendarAdapter` protocol. Replacement: direct `ProviderMappingAdapter` return type.
  - Verification after simplification: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_provider_fixtures.py` passed `12 passed, 1 warning`; `cd apps/server && uv run --extra dev ruff check src/twobrain_rec_server/calendar/adapters.py tests/unit/test_calendar_provider_fixtures.py` passed; full local CI passed afterward.
  - net: `-14` lines applied.
- T135 final checklist re-run:
  - Re-read `specs/060-calendar-context-ingestion/checklists/calendar-integration.md` CHK001-CHK044 against final implementation and supporting artifacts.
  - Result: all CHK001-CHK044 remain satisfied; no blocker found.
  - Placeholder scan over `spec.md`, `plan.md`, `research.md`, `provider-deep-dive.md`, `data-model.md`, contracts, quickstart, tasks, and checklists found no unresolved implementation placeholders. The remaining open task is PR/GitHub closeout only.
- T136 pre-closeout verification:
  - `tasks.md` status after T133-T135: 135 of 136 tasks complete; T136 remains open.
  - `gh issue list --state all --search "060 calendar" --limit 100` found open feature `060` GitHub issues, including T133, T134, T135, and T136 tracker issues.
  - `gh pr list --state all --search "060-calendar-context-ingestion" --limit 20` found no PR for this branch.
  - No GitHub issues were closed in this implementation pass because issue closure requires the matching task to be `[X]`, PR/review evidence, and a clear Russian closure comment. PR/release notes remain the next closeout layer after commit/push/PR creation.
