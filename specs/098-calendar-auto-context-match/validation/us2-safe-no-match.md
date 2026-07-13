# Feature 098 US2 Safe No-Match Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T035-T047
**Requirement trace**: FR-002-FR-005, FR-008-FR-013, FR-017-FR-019,
FR-028-FR-037, FR-042-FR-044, FR-048-FR-049, FR-052; SC-004,
SC-005, SC-010, SC-011

## Result

US2 is ready. Weak, protected, all-day, cancelled, deleted, zero-duration,
stale, latest-failed, manual-upload, offline/recovery, missing-attempt and
cross-workspace inputs now degrade to a durable, truthful no-context outcome.
They do not trigger retrospective matching and do not block meeting creation,
upload, processing or the local Record/Stop path.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as US2
evidence. The privacy, authorization and forbidden-content checks below are
ordinary feature acceptance tests only.

## Test-First Receipts

The bounded integration/contract red run produced the intended implementation
gaps:

```text
3 failed, 4 passed, 58 deselected
```

The same five complete files initially produced:

```text
3 failed, 62 passed
```

The failures proved that manual uploads did not yet return/persist their
`skipped_manual_upload` projection and that private resolve did not yet create
a metadata-only audit row. Missing-attempt recovery, foreign-attempt
indistinguishability, provider fail-soft behavior and protected zero-detail
responses were already green and were retained as regression receipts.

Two separate cabinet checks then failed at the intended boundary because
`calendar_context_summary` had no owner-detail mode and the safe summary had no
owner-only reason field. Two settings checks likewise failed because the 098
eligibility boundary helper and exact product copy were absent.

A final audit/projection pin caught two additional contract defects before
acceptance: resolve audit incorrectly claimed a user override was preserved,
and the new optional owner-detail field initially appeared as `null` in generic
meeting responses. The implementation now omits the override flag unless an
authoritative user/upload/file/legacy title was actually preserved, and omits
the optional reason field entirely when it is unavailable. Consumption audit
also carries the attempt's exact freshness class instead of substituting
`current`.

The ten added matcher eligibility cases and four new Swift recovery/queue cases
were green on first execution because the preceding US1 matcher and queue work
already satisfied those negative boundaries. This is recorded as pre-existing
coverage, not represented as a fabricated red result.

## Final Server Receipt

The final US2-focused server command was:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_calendar_provider_failures.py \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_calendar_settings_view_models.py
```

Accepted result:

```text
177 passed, 1 existing StarletteDeprecationWarning in 6.41s
```

The warning is upstream `starlette.testclient`/`httpx` deprecation noise. No
feature assertion, fixture, database or collection warning remains.

The canonical OpenAPI receipt was rerun separately after the owner-only safe
reason projection was added:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_openapi_contract_drift.py
```

Result:

```text
9 passed, 1 existing StarletteDeprecationWarning in 8.71s
```

## Eligibility And Fail-Soft Receipt

The server tests prove:

- weak title/time signal never becomes a candidate;
- private and free/busy-only rows expose zero candidates, zero title/roster
  detail and only the bounded `private_free_busy_skipped` reason;
- all-day, cancelled, provider-deleted and non-positive-duration rows are
  ineligible;
- a source older than 24 hours fails closed; exactly 24 hours remains current;
- a failed sync newer than the last success produces `latest_sync_failed`;
- any stale/latest-failed selected source vetoes a partial-source winner;
- feature 063 preview filters do not weaken 098 automatic eligibility;
- provider failure returns a safe calendar outcome while meeting creation and
  processing remain successful;
- a missing, invalid, foreign, expired or already-consumed attempt creates
  `skipped_offline_or_unknown` without querying current calendar state;
- manual upload creates `skipped_manual_upload` and preserves
  `upload_provided` or `file_name_derived` title provenance;
- private provider text, credentials, raw event IDs, attendee values, meeting
  links, passcodes and provider payloads do not enter response or audit data.

## Owner-Only Product Truth

Recording-list and non-owner review projections remain generic. Even an owner
meeting-detail response keeps its embedded list item generic; only the
authorized top-level detail projection receives bounded safe reason copy.
Private reason text is absent from list HTML and list accessibility text.

The allowed owner-detail copy is mapped from safe reasons to product language,
including:

- `Приватное событие пропущено`;
- `Данные календаря устарели`;
- `Календарь недоступен`;
- `Ручная загрузка не сопоставляется`;
- `Офлайн-запись не сопоставляется`;
- `Подходящая встреча не найдена`.

Internal enum names and provider failures never become user-facing copy. The
rendering reuses existing GRAF `state-row`, `chip`, `truth-copy` and
`state-list` primitives and adds no new visual system.

The existing calendar settings surface now contains the exact boundary helper:

```text
Эти фильтры управляют подсказками и списком ближайших встреч. Приватные события и события на весь день не используются для автоматического контекста записи.
```

It is rendered once under the existing `Фильтры и ограничения` section with
the existing `calendar-policy-note` primitive.

## Metadata-Only Audit Receipt

Resolve and consumption write bounded `calendar_match_resolved` and
`calendar_match_consumed` events. The accepted payload is limited to outcome,
safe reason, matcher version, bounded candidate/roster counts, exact freshness
class, decision source and relevant booleans.

The latest-failure integration receipt proves both events retain:

```text
latest_sync_failed
```

Private resolution records candidate count zero and no event/title/roster
identifier. Manual/offline paths may omit freshness because no live match
attempt exists; they do not invent a current calendar evaluation. Audit
persistence remains inside the same database transaction and does not turn a
calendar degradation into meeting/upload/processing failure.

The post-audit SC-017 atomic consumption benchmark remained below its 50 ms
threshold at p95 `2.248375 ms` over 100 measured consumptions; the exact receipt
is retained in `us1-clear-match.md`.

## macOS Recovery And Queue Receipt

The final feature filter was:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CalendarAutoContextMatch|DesktopUploadClient|DesktopUploadQueue|DesktopCalendarReminder|CaptureControl|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Result:

```text
187 tests, 0 failures
```

The receipts prove that a resolve failure releases the queued recording,
retries preserve truthful attempt absence, recovery scans never run
retrospective calendar resolve, no fabricated attempt ID enters the create
payload, and an otherwise valid recording remains uploadable. Existing visible
capture state and one-action Stop behavior remain unchanged.

## Focused Lint

Focused Ruff covered the changed server API, calendar, cabinet and database
packages plus the US1/US2 test surfaces. Result:

```text
All checks passed!
```

`git diff --check` also returned clean.

## US2 Exit Decision

- Strict weak/protected/all-day/deleted eligibility: PASS.
- Stale/latest-failed whole-source veto: PASS.
- Manual-upload and offline/recovery durable skip truth: PASS.
- Cross-workspace attempt indistinguishability: PASS.
- Generic list/non-owner and safe owner-detail projection: PASS.
- Metadata-only exact-freshness audit: PASS.
- Meeting/upload/processing/capture fail-soft behavior: PASS.
- Swift recovery queue without fabricated attempts: PASS.
- Deferred standalone security audit: unchanged and not represented as done.

US2 may exit to the ambiguity, correction and durable-clear story.
