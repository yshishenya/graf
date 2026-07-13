# Feature 098 US5 Recurring Context Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T075-T083
**Requirement trace**: FR-004, FR-024-FR-026, FR-030, FR-045, FR-048;
SC-005, SC-009

## Result

US5 is ready. GRAF stores only a workspace/source-scoped SHA-256 series key,
selects the latest strictly earlier matched occurrence, and applies the normal
meeting access decision to that predecessor independently. The projection is
limited to meeting ID, safe title, recording start and bounded readiness.
Transcript text, summary excerpts, roster content, provider identifiers and
calendar descriptions are never copied into recurring context.

An inaccessible or deleted latest predecessor returns no pointer and does not
fall back to an older visible occurrence. Same-user meetings in another active
space and meetings in another workspace are excluded before projection. The
browser cabinet and the embedded macOS cabinet reuse the same server-owned
list/detail routes and the same `В серии` pointer component.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as US5
evidence. The access and no-leak cases below are ordinary feature acceptance
tests.

## Test-First Receipts

### Series identity and deterministic ordering

The T075 baseline was:

```text
16 passed, 1 existing StarletteDeprecationWarning
```

Four synthetic US5 cases then produced:

```text
1 failed, 3 passed, 16 deselected
```

Provider-series hashing, iCalendar UID fallback with recurrence evidence and
missing/ambiguous metadata behavior were already green from the US1 matching
foundation. The real RED was the absent deterministic predecessor-ordering
helper. The bounded implementation filters with strict `< current` and sorts
by occurrence start descending with UUID descending as the stable tie-breaker.
Final unit receipt:

```text
20 passed, 1 existing StarletteDeprecationWarning
```

### Independent predecessor authorization

The two-file T076 baseline was:

```text
34 passed, 1 existing StarletteDeprecationWarning
```

The five new owner, non-owner, deleted, inaccessible and cross-space scenarios
initially produced:

```text
2 failed, 3 passed, 34 deselected
```

The two failures were the missing authorized owner/team pointers. The three
deny cases were already safely null and pinned the non-negotiable behavior:
no placeholder, no older fallback and no predecessor ID/title existence leak.
After implementation:

```text
5 passed, 34 deselected, 1 existing StarletteDeprecationWarning
```

### API contract and server rendering

The T077 baseline was:

```text
20 passed, 1 existing StarletteDeprecationWarning
```

Five new metadata-bound, authorized, deleted/no-leak and web/embedded render
checks produced:

```text
2 failed, 23 passed, 1 existing StarletteDeprecationWarning
```

The RED gaps were the null authorized API pointer and missing `В серии` UI.
The schema bound and deleted/no-leak checks were already green. Final focused
contract and detail results were:

```text
3 passed, 7 deselected
2 passed, 13 deselected
```

The rendered link is `Предыдущая встреча · {локальная дата}` and its accessible
label contains the safe predecessor title, date and readiness. Deleted or
denied predecessors produce no block, disabled placeholder, data attribute or
route.

### Browser and embedded route parity

The T082 baselines were:

```text
server meeting list: 14 passed
macOS DesktopCabinetUploadLinkTests: 10 tests, 0 failures
```

The new server-owned `Ближайшие` scenario first produced one expected failure:
the section still contained only its empty state. The new macOS policy test was
green immediately because the existing embedded route policy already allowed
the list-to-detail transition. No native production code was necessary.

Final focused results:

```text
server recurring list parity: 1 passed, 14 deselected
macOS DesktopCabinetUploadLinkTests: 11 tests, 0 failures
```

The web pointer targets `/meetings/{previous}` and the embedded pointer targets
`/desktop/meetings/{previous}`. Both are rendered from the same bounded list
read model and shared pointer helper. The existing GRAF card, section-title,
muted-text and mini-link primitives are reused; no parallel visual system or
native review screen was added.

## Accepted Read Model

For a current `matched_auto` or `matched_user` row with a non-null series hash
and occurrence start, the query:

1. remains inside the current workspace/space;
2. considers only `matched_auto`/`matched_user` rows with the same hash;
3. requires `matched_event_starts_at < current`;
4. selects exactly the newest row, with context UUID as deterministic tie-break;
5. applies `decide_meeting_access` to that selected previous meeting;
6. returns null immediately when the selected predecessor is deleted or denied.

The query deliberately does not continue to an older occurrence after a denial.
That preserves latest-occurrence semantics and avoids turning authorization
differences into a fallback/existence signal.

`PreviousRecurringMeetingView` remains `extra=forbid` and contains only:

- `meeting_id`;
- `safe_title`;
- `started_at`;
- `readiness_state`: `notes_ready`, `transcript_ready`, `processing` or
  `unavailable`.

Readiness is derived from already-authorized artifact state. No transcript,
summary, roster, calendar description, meeting URL, passcode or provider key is
present in the schema or HTML.

## Final US5 Regression Receipt

The final six-file server slice covered unit identity/order behavior, owner and
team authorization, deleted/inaccessible/cross-space denial, bounded OpenAPI
projection, context/review APIs, web/embedded detail rendering and the
server-owned upcoming list:

```sh
cd apps/server
uv run pytest -q \
  tests/unit/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_auto_context_match.py \
  tests/integration/test_calendar_access_policy.py \
  tests/contract/test_calendar_auto_context_contract.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_meeting_list.py
```

Accepted result:

```text
99 passed, 1 existing StarletteDeprecationWarning in 46.89s
```

The canonical OpenAPI and cabinet contract follow-up passed after adding the
bounded list projection and reconciling pre-existing 098 detail fields:

```text
16 passed, 1 existing StarletteDeprecationWarning in 15.18s
```

macOS route receipt:

```sh
cd apps/macos
swift test --filter DesktopCabinetUploadLinkTests
```

```text
11 tests, 0 failures
```

Focused Ruff covered all changed US5 Python production and test files:

```text
All checks passed!
14 files already formatted
```

`git diff --check` returned clean.

## US5 Exit Decision

- Workspace/source-scoped hashed series identity: PASS.
- iCalendar UID fallback only with recurrence evidence: PASS.
- Latest strictly earlier deterministic selection: PASS.
- Independent owner/team predecessor authorization: PASS.
- Deleted/inaccessible latest predecessor without older fallback: PASS.
- Same-user other-space and cross-workspace isolation: PASS.
- Metadata-only API/readiness projection: PASS.
- No transcript/summary/roster/provider-content leak: PASS.
- Shared `В серии` review and `Ближайшие` pointer: PASS.
- Browser/embedded server-route parity: PASS.

US5 is complete and ready for the next 098 story. Feature-level PR, commit,
release and deployment remain outside this story checkpoint.
