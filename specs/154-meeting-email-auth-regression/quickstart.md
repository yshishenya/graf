# Quickstart Validation

## Capture

1. From `apps/macos`, run focused meeting detection tests.
2. Build `swift build --package-path apps/macos --product TwoBrainRecApp`.
3. Run the local app with `apps/macos/Scripts/run-local-app.sh` against the local
   server. Use a verified native target and an active assisted policy for timeout
   and saved-target start; confirm prompt/button behavior with metadata-only logs.
4. End the synthetic target and wait beyond the 15-second detector grace period;
   confirm one stop, one finalization and no active session remains.

## Email auth

1. Start local services using `infra/scripts/start-local.sh`.
2. In the embedded cabinet, submit an existing local identity email.
3. Enter `000000` only on the local loopback profile; verify redirect to meetings.
4. Confirm the local cookie is available to the native client and that production
   tests still assert Secure `__Host-` behavior.

## Closeout

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_web_owner_session_context.py \
  -k 'browser_email_login or email_code' \
  tests/unit/test_local_email_login_code.py \
  tests/unit/test_email_login_delivery.py
swift test --package-path apps/macos --filter MeetingDetection
swift build --package-path apps/macos --product TwoBrainRecApp
infra/scripts/ci-local.sh
```
