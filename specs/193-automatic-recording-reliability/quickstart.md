# Quickstart: Verify Automatic Recording Reliability

Use synthetic targets/metadata only. Do not record private content, change
production configuration or replace `/Applications/GRAF.app`.

## 1. Focused regression suites

```sh
cd apps/macos
swift test --filter 'MeetingDetectionPolicyTests|MacOSAudioOwnershipParserTests|DesktopUploadClientTests'
```

Expected: source identity/order, consumer acknowledgement/retry, current auth
gate and cookie reconciliation/selection tests pass.

## 2. Source-order matrix

For one verified bundle, run both sources in every start/end order. Confirm:

- exactly one eligible trigger after debounce;
- ending one source does not end the candidate;
- all-source end plus grace emits one `ended`;
- duplicate events do not duplicate trigger/start/stop;
- a new later meeting of the same bundle is eligible.

## 3. Policy and retry matrix

With missing/expired/mismatched policy or acknowledgement, confirm no countdown
promise appears. With a valid exact pair, reject the first offered trigger using
each retryable blocker, clear it while the source remains active and confirm a new
offer within 2 seconds. Confirm accepted prompt, Skip and manual Stop do not recur
until a real end boundary.

## 4. Observer lifecycle

Start the dev app during synthetic active attribution, then:

1. Confirm snapshot creates the normal debounced candidate. Historical
   intermediate transitions must not create offers; only the final complete
   sensor attribution state is applied. A snapshot that exceeds 3.5 seconds,
   is redacted or truncated must proceed fail-closed to live observation.
2. Terminate only its child `/usr/bin/log stream` process.
3. Confirm one restart (not two) and new live events within 5 seconds.
4. Trigger sleep/wake or the test seam and confirm a fresh snapshot/live generation.
5. Stop detection deliberately and confirm no child respawns.

## 5. Auth lifecycle

Using fixtures, exercise login, replacement, logout and re-login with same-name
cookies of different domain/path/expiry/secure attributes. Confirm the old value
cannot be selected after reconciliation, logout leaves no applicable native auth,
and no general `Cookie` request header or diagnostic value is produced.

## 6. Repository gates

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

## 7. Separate dev build

```sh
sh apps/macos/Scripts/build-local-app.sh --open
```

Verify the dev app only. Production policy/deploy/signing/release remain outside
this feature and require a separate approval gate.
