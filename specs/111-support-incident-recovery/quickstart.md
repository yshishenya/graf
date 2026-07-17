# Quickstart validation: support incident recovery

## Preconditions

- Work on `codex/111-support-incident-recovery`.
- Use synthetic metadata-only support payloads and fake GitHub clients only. Do not use an actual meeting, audio, transcript, secret, private URL or live session token in tests or evidence.

## Focused server validation

```sh
cd apps/server
PYTHONPATH=src bash scripts/run_local_postgres_tests.sh -q \
  tests/integration/test_support_incidents.py \
  tests/contract/test_support_incident_contract.py \
  tests/unit/test_support_incident_redaction.py \
  tests/unit/test_support_incident_github_issue_body.py \
  tests/integration/test_health_readiness.py
```

Prove:

1. Cookie-authenticated + valid CSRF request gets a `CUST-*` number and a private Issue link.
2. GitHub failure returns `202 pending_sync` after the incident is stored; the sync route later succeeds using only the number.
3. Legacy headers remain rejected in production and a missing/invalid CSRF token remains rejected.
4. Unsafe fields never enter DB/Issue output.

## Focused macOS validation

```sh
cd apps/macos
swift test --filter 'TwoBrainRecSharedTests.DesktopUploadQueueTests'
swift test --filter 'TwoBrainRecSharedTests.DesktopUploadClientTests'
swift test --filter 'TwoBrainRecSharedTests.EmbeddedCabinetSupportIncidentBridgeTests'
swift build
```

Prove:

1. `pending_sync` persists across queue reload and can become `sent` after status retry.
2. The native bridge has a fixed same-origin endpoint, uses argument-based WebKit execution and does not copy cookies or emit CSRF/session values.
3. Accepted, pending, rejected and sign-in-required copy are distinct, localized and accessible. Rejected reports expose only the existing safe clipboard summary.

## Repository gate

```sh
infra/scripts/ci-local.sh
```

## Release-only live proof (not part of this implementation approval)

After an approved server release and an installed updated macOS build, sign into the embedded cabinet, trigger a synthetic safe custody failure, and verify:

1. Desktop displays a `CUST-*` number.
2. The server record is metadata-only.
3. A private Issue contains the expected structured fields and no forbidden content.
4. A second press deduplicates rather than creates a second Issue.

Do not record live IDs, private Issue URLs, payloads, tokens, cookies or meeting content in committed evidence.
