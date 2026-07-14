# Feature 098 US1 Clear-Match Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T017-T034
**Requirement trace**: FR-001-FR-008, FR-016-FR-018, FR-020-FR-022,
FR-027, FR-030-FR-033, FR-035, FR-040, FR-043-FR-044, FR-046-FR-049,
FR-052; SC-001, SC-002, SC-005, SC-007, SC-011, SC-014, SC-017

## Result

US1 is ready. A live first-party recording can resolve one current eligible
calendar event without blocking capture, persist an opaque attempt through the
desktop queue, consume it once in meeting creation, and project immutable safe
calendar context in browser and embedded cabinet surfaces.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed, or counted as US1
evidence.

## Red-Green Receipt

The first bounded server run produced the intended contract red state:

```text
14 failed, 1 warning in 6.65s
```

Every failure was caused by the not-yet-implemented matcher, resolve route,
consumption path, or canonical OpenAPI projection. There was no fixture,
database, dependency, or test-collection failure.

The first bounded Swift run stopped at the intended compile-red boundary for
the absent resolve/attempt models and queue/client wiring. The Swift toolchain,
package resolution, and existing test setup loaded successfully.

After implementation, the exact core server command was:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_auto_context_match.py \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/integration/test_calendar_auto_context_match.py
```

Accepted result:

```text
14 passed, 1 existing StarletteDeprecationWarning in 3.88s
```

The warning is upstream `starlette.testclient`/`httpx` deprecation noise. No
feature assertion, fixture, persistence, or setup warning remains.

## Resolve, Attempt, And Meeting Transaction

The server receipts prove:

- exactly one fresh high-confidence event becomes `matched_auto`;
- the five-minute pre-start result remains provisional until actual recording
  overlap is known;
- an early stop before event start rejects the provisional match;
- four selected sources and at most 50 rows are evaluated deterministically;
- duplicate rows collapse only through strong conference-link or same-source
  recurrence identity, never a weak cross-source provider ID;
- the resolve route requires principal plus device authentication and an
  `Idempotency-Key`, while correctly remaining outside browser CSRF handling;
- a repeated key and identical request returns the same opaque attempt, while
  changed input returns an explicit conflict;
- resolve reads persisted snapshots only and performs no provider network I/O;
- first-party meeting creation consumes the exact same-owner, same-workspace,
  same-recording attempt in its database transaction;
- a retry preserves the original create-request fingerprint even after a safe
  calendar title replaces a generic/app title;
- only replaceable title sources accept the calendar title;
- the roster snapshot contains bounded display-safe values and no raw email;
- the attempt is consumable one microsecond before expiry and rejected exactly
  at `evaluated_at + 24 hours`;
- one authoritative context row is created and an attempt cannot be consumed
  twice.

The durable fingerprint and revised migration were rechecked with:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_auto_context_migrations.py \
  tests/integration/test_persistent_ingest_storage.py
```

Result:

```text
14 passed, 1 existing StarletteDeprecationWarning in 4.46s
```

The disposable PostgreSQL/RLS gate was repeated after this evidence because
the migration gained the durable create-request fingerprint. The rebuilt image
was `sha256:010e102090a5ddcbe394fe8deca21ce3a06024665daa691e799d0b324609c66b`.
The accepted run returned `rls_validation_result=pass`,
`ready_for_production_truth=true`, and `migration_verification_result=pass`.
PostgreSQL catalog checks proved the nullable fingerprint at 0021, its absence
after downgrade to 0020, and a clean upgrade back to 0021. All disposable
containers, volumes, network, image, and ignored synthetic secret files were
then removed.

## SC-017 Performance Receipt

The benchmark cases were warmed before measurement and used only synthetic
data. The resolve case used exactly four selected sources, 50 candidate rows,
and 100 measured evaluations. The consumption case used one warm-up followed
by 100 measured same-transaction atomic consumptions.

Accepted command:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q -s \
  tests/unit/test_calendar_auto_context_match.py::test_sc017_one_hundred_warmed_resolves_are_within_200ms_p95 \
  tests/integration/test_calendar_auto_context_match.py::test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95
```

Accepted result:

```text
resolve samples=100, p95=0.620042 ms, threshold<=200 ms
atomic consumption samples=100, p95=2.248375 ms, threshold<=50 ms
2 passed, 1 existing StarletteDeprecationWarning in 0.48s
```

The atomic-consumption value was remeasured after metadata-only audit
persistence was added in US2; the earlier pre-audit value was 1.438542 ms.
The temporary print instrumentation used to capture both exact values was
removed after the receipts; both tests retain their threshold assertions.

## Canonical API And Cabinet Projection

The post-implementation contract command was:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_openapi_contract_drift.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/contract/test_cabinet_contract.py
```

Result:

```text
73 passed, 1 existing StarletteDeprecationWarning in 22.49s
```

The focused list/review/render/access command recorded by the independent
test worker passed:

```text
8 passed, 1 existing StarletteDeprecationWarning in 2.84s
```

Those receipts prove one safe `MeetingCalendarContextSummary` shape across
list and review, immutable roster projection, protected-state suppression,
unchanged `SPEAKER_00` and owner access, legacy-link compatibility, and exact
`Из календаря` rendering once in normal and embedded list/detail surfaces.
The implementation reuses existing GRAF `state-row`, `chip`, `truth-copy`, and
`state-list` primitives; it introduces no new visual system or copied product
surface.

## macOS Capture And Queue Receipt

Root reran the bounded US1 filter:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CalendarAutoContextMatchTests|DesktopUploadClientTests|DesktopUploadQueueTests'
```

Result:

```text
95 tests, 0 failures in 0.177s (0.185s selected-test wall time)
```

The implementation starts the resolve request only after local capture becomes
active, never waits on calendar resolution to expose recording truth or begin
upload processing, and degrades to no attempt on failure. A successful attempt
is persisted only while the queued item is still safe to enrich; once upload
begins, a late resolve cannot change the idempotent meeting-create identity.
Desktop logs contain only local IDs, state, and safe reason codes; no calendar
payload, provider credential, raw attendee value, transcript, or audio is
logged.

## US1 Exit Decision

- Deterministic clear current/pre-start matching: PASS.
- Strong-identity dedupe and bounded snapshot-only reads: PASS.
- Idempotent resolve plus durable create retry fingerprint: PASS.
- Atomic same-tenant consumption and exact 24-hour boundary: PASS.
- Non-blocking capture and durable desktop queue propagation: PASS.
- Immutable safe list/review/browser/embedded projection: PASS.
- SC-017 warmed p95 thresholds: PASS with exact values above.
- Deferred standalone security audit: unchanged and not represented as done.

The repeated PostgreSQL migration/RLS verification closes the migration delta.
US1 may exit to the safe no-match/degraded-outcome story.
