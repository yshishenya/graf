# Feature 098 US3 Ambiguity And Correction Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T048-T063
**Requirement trace**: FR-006-FR-016, FR-027-FR-039, FR-042-FR-049,
FR-051-FR-052; SC-003, SC-006-SC-008, SC-010-SC-011, SC-015

## Result

US3 is ready. A single safe candidate remains automatic, ambiguity requires an
explicit owner choice, and continuing without context is persisted separately
from a later clear. Explicit select, correct and clear operations serialize on
the single meeting context row, retain immutable meeting-owned snapshots and
produce one metadata-only audit receipt per accepted owner action.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as US3
evidence. The authorization, CSRF and forbidden-content checks below are
ordinary feature acceptance tests only.

## Test-First Receipts

The API/authorization RED worker first proved the existing baseline:

```text
22 passed
```

The new GET/PUT/DELETE and access cases then produced the intended gaps:

```text
6 passed, 7 failed
```

The failures pinned the missing GET projection, legacy `linked`/`unlinked`
response states and absent explicit-action audit receipts.

The cabinet RED worker retained its existing baseline:

```text
61 passed
```

and the six new chooser, non-owner, accessibility and localization assertions
all failed before implementation:

```text
6 failed
```

The macOS RED worker produced:

```text
4 failed, 1 passed; 9 assertion failures
```

Those failures isolated missing decision-intent and event-ID propagation from
the prompt into the recording path. The already-green assertion proved that
visible capture truth remained intact.

## Final Server Receipt

The final combined US3 server command covered the calendar contract, OpenAPI
drift, CSRF, selection/concurrency/access policy, cabinet view models, shell,
list and detail integration surfaces:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_openapi_contract_drift.py \
  tests/integration/test_cabinet_csrf.py \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_access_policy.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py
```

Accepted result:

```text
163 passed, 1 existing StarletteDeprecationWarning in 77.93s
```

After the final mechanical formatting pass, the directly affected view-model
file was rerun:

```text
33 passed, 1 existing StarletteDeprecationWarning in 0.13s
```

The canonical OpenAPI drift receipt was also run separately:

```text
9 passed, 1 existing StarletteDeprecationWarning
```

The warning is upstream `starlette.testclient`/`httpx` deprecation noise. No
feature assertion, collection, fixture or database warning remains.

## Safe Explicit Candidate Receipt

Explicit selection reuses the same strict candidate boundary as automatic
matching. A focused six-case receipt proves that a user cannot force-select:

- a private event;
- an all-day event;
- a cancelled event;
- a provider-deleted event;
- an event with non-positive duration;
- an event with insufficient title/time signal.

Result:

```text
6 passed
```

The selected row must also belong to the meeting owner and workspace, remain
under the selected active source and be represented only by the safe candidate
projection. Foreign event IDs remain indistinguishable from unavailable or
ineligible choices.

## Durable Choice, Concurrency And State Truth

The accepted API behavior is:

- `GET /api/v1/meetings/{meeting_id}/calendar-context` returns the canonical
  owner-safe projection and owner-only candidates/actions;
- `PUT` selects or corrects one safe candidate and returns `matched_user`;
- `DELETE` creates or updates the single row to `cleared_by_user`;
- start-time `declined_by_user` remains distinct from a later
  `cleared_by_user` action;
- repeated clear is idempotent;
- select/correct/clear lock the meeting and context rows before mutation;
- two concurrent owner selections leave one context row and two immutable
  metadata-only action audits, with the serialized final owner choice;
- a user/upload/file/legacy authoritative title is never overwritten, while a
  calendar/app-context/generic title may follow an explicit correction;
- title, roster, time, series and source values are copied into the meeting
  snapshot instead of being read back from mutable provider state.

Non-owners receive the normal not-found/access-policy result and no candidate,
reason, protected state or action capability. Public/list projections mask
protected internal states and expose no private provider detail.

## Cabinet And Accessibility Receipt

The server-owned browser and embedded cabinet share the same owner-only HTMX
actions for choose, continue without context and clear. The existing calendar
router registration already covered the new handlers, so no redundant
registration edit was introduced. CSRF remains mandatory and non-HTMX
submissions redirect back to the meeting detail.

The main column now contains a native `fieldset`/`legend` ambiguity chooser
with radio labels, safe title/source/time content, `aria-describedby`,
`aria-live`, deterministic focus and responsive layout. Initial ambiguity focus
lands on the chooser; successful choose/correct/clear HTMX mutations return
focus to the `Контекст встречи` heading. List ambiguity exposes only a compact
owner action; the bounded owner-only reason remains on detail. Matched context
uses an inspector, bounded safe match-time title/event interval and a
stable-title clear confirmation. The recording timezone offset is used for
candidate display rather than the server's local timezone.

Exact RU/EN state copy is covered for `matched_user`, `ambiguous`,
`no_context`, `declined_by_user` and `cleared_by_user`. Rendering reuses the
existing GRAF variables and primitives; no separate visual system, custom icon
set or browser-only workflow was introduced.

## macOS Intent And Capture-Truth Receipt

The final focused command was:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CalendarAutoContextMatch|DesktopUploadClient|DesktopUploadQueue|DesktopCalendarReminder|CaptureControl|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Result:

```text
195 tests, 0 failures in 0.700s (0.715s selected-test wall time)
```

One safe prompt proceeds with automatic intent and no explicit event ID.
Overlap selection carries `userSelected` plus the selected event ID, while
continue-without-context carries `userDeclined` and no event ID. The server
attempt persists that decision intent; the desktop queue keeps only the opaque
attempt ID and selected event ID actually consumed by later transport. Retry
and recovery preserve those IDs without duplicating dead intent state. Direct
prompt-closure tests and a small pure capture-to-resolve policy replace brittle
source-string assertions. The embedded route policy accepts the three
server-owned meeting action paths. Manual Record/Stop, active-capture
visibility and one-action Stop behavior are unchanged.

## Focused Lint And Diff Hygiene

Focused Ruff covered all changed US3 server and test files:

```text
All checks passed!
```

Ruff format check reports:

```text
18 files already formatted
```

`git diff --check` also returned clean.

## US3 Exit Decision

- Single automatic prompt and explicit overlap/no-context intent: PASS.
- Owner-only GET/PUT/DELETE and CSRF boundary: PASS.
- Strict explicit candidate eligibility and workspace/source ownership: PASS.
- Serialized correction/clear with one context row: PASS.
- Distinct `declined_by_user` and `cleared_by_user`: PASS.
- Immutable safe snapshot and authoritative-title precedence: PASS.
- Generic non-owner/list projection with no existence/private leak: PASS.
- Browser/embedded parity, accessibility and RU/EN copy: PASS.
- Durable macOS choice without capture-truth regression: PASS.
- Deferred standalone security audit: unchanged and not represented as done.

US3 may exit to stable title and context-history validation.
