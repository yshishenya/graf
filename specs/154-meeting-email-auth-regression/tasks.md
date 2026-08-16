# Tasks: Feature 154

## Setup and regression tests

- [X] T001 [P] [US1] Validate detector policy tests and app preflight proving prompt eligibility is independent of prior assisted acknowledgement while automatic actions remain gated in `apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift` and `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T002 [P] [US1] Validate countdown/lifecycle tests for prompt cancellation, one-shot timeout and target-end idempotency in `apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift` and existing detector tests.
- [X] T003 [P] [US3] Add production/local cookie-name and session-token tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.
- [X] T004 [P] [US3] Validate email integration and WebKit/native session contract with `apps/server/tests/integration/test_web_owner_session_context.py` and macOS cabinet tests.

## Capture lifecycle

- [X] T005 [US1] Separate detector prompt preflight from assisted automatic-start authorization in `apps/macos/RecApp/App/TwoBrainRecApp.swift` while preserving existing policy gates.
- [X] T006 [US1] Preserve explicit prompt-button start while re-checking current policy/acknowledgement for timeout and saved-target starts in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T007 [US2] Preserve scoped, idempotent target-end stop/finalization under concurrent detector outputs in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.

## Email session integration

- [X] T008 [US3] Make desktop cookie synchronization choose the server cookie from the actual loopback/production origin in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift`.
- [X] T009 [US3] Make native desktop requests recognize the same local cookie without changing the server auth flow in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`.

## Validation

- [X] T010 [US1] Run focused and full Swift tests plus macOS product build.
- [X] T011 [US3] Run focused/full local Postgres email-auth tests and Python compile/lint checks.
- [X] T012 [US1] [US2] [US3] Run local app/email smoke checks and `infra/scripts/ci-local.sh`; leave implementation uncommitted pending explicit approval.
