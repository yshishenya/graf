# Quickstart: Verify Assisted Auto-Start Hardening

## Preconditions

- Use only synthetic meeting targets and metadata.
- Do not capture private meeting content while validating.
- Keep production deploy switches unchanged.

## 1. Server contract

Run focused tests for meeting detection config and registry response. Verify:

- default/missing configuration omits policy;
- wrong workspace omits policy;
- matching internal workspace returns active policy;
- expired policy is omitted;
- ETag changes when policy changes;
- response contains no raw workspace ID or unsafe content.

## 2. Acknowledgement migration

Start with an existing settings fixture containing selected target IDs but no
acknowledgement. Verify targets remain selected and assisted start is blocked.
Accept the current policy in settings, reload from disk and verify exact match.
Change acknowledgement version and verify a new acceptance is required.

## 3. Countdown behavior

With an active policy and acknowledgement:

1. Emit a synthetic verified native target.
2. Verify visible `8` seconds and automatic-start copy.
3. Advance controlled time to 7.999 s: no start.
4. Advance to 8.000 s: exactly one `prompt_timeout` start.
5. Repeat with Start, Skip, disappearance and policy revocation before timeout;
   no late duplicate start is allowed.

## 4. Saved target and evidence

Enable one target through «Всегда писать это приложение». Verify its direct start
uses `saved_target_policy`. Verify button uses `prompt_button`. Inspect synthetic
session evidence for policy/ack versions and ensure timeout/saved starts are not
labelled as user button confirmation.

## 5. Storage and current gates

Inject healthy and critical storage probe results. Critical/unknown measurement,
permission loss, target end, active recording, missing indicator or missing Stop
must block before capture. Healthy unchanged state may start once.

## 6. Accessibility and manual smoke

Using VoiceOver, verify the remaining whole seconds and automatic-start
consequence are announced. Confirm local indicator appears and Stop is reachable
in one action before recorded frames are accepted.

## 7. Repository validation

```sh
infra/scripts/ci-local.sh
```

Do not run production CD or enable runtime policy without separate approval.
