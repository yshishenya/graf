# Feature 098 US6 Speaker Deferral Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T084-T090
**Requirement trace**: FR-020-FR-026, FR-040, FR-044-FR-045; SC-008

## Result

US6 is ready. Calendar participants remain an authorized, bounded roster
projection and never become speaker identity, meeting permission, share state,
recipient state or delivery work. Transcript and diarization labels remain
canonical `SPEAKER_XX` values even when synthetic calendar input carries names
or speaker-like fields.

The browser cabinet and embedded macOS cabinet reuse the same server-owned
calendar-context component. An available roster is headed
`Участники из календаря · N` and carries the exact helper copy
`Приглашённые участники, не подтверждённые спикеры`. The roster remains outside
the transcript and speaker panels. Existing GRAF section-title, state-row and
muted-text primitives are reused; no parallel visual system or native review
screen was added.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as US6
evidence. The authorization and no-side-effect checks below are ordinary
feature acceptance tests.

## Test-First Receipts

### T084: roster metadata versus speaker truth

The pre-existing unit files were green:

```text
cabinet view models: 33 passed, 1 existing StarletteDeprecationWarning
calendar participants: 2 passed, 1 existing StarletteDeprecationWarning
```

The two new US6 cases were also green immediately:

```text
2 passed, 33 deselected
full two-file slice: 35 passed
```

There was no real RED and none is fabricated. The existing boundary already
canonicalized raw diarization labels to `SPEAKER_00`/`SPEAKER_01` and the
calendar normalizer already discarded injected `speaker_label`, transcript,
diarization, access, share and send hints. The new tests pin that behavior and
prove calendar display names survive only in `calendar_roster`.

### T085: zero permission, share and delivery side effects

The integration baseline was:

```text
12 passed, 1 existing StarletteDeprecationWarning in 5.74s
```

Two new 25-participant roster-heavy cases were green immediately:

```text
2 passed, 12 deselected, 1 existing StarletteDeprecationWarning in 1.19s
full two-file slice: 14 passed, 1 existing StarletteDeprecationWarning in 6.91s
```

Again there was no real RED: the current access/share architecture already
kept roster metadata inert. The cases preserve `owner_only` visibility and the
workspace membership count, deny the synthetic attendee with privacy-safe
`404 meeting_not_found`, and emit no raw participant email in responses.

### T086-T087: API/UI separation and exact roster copy

The contract/detail baseline was:

```text
22 passed
```

After adding three US6 checks, the first result was:

```text
1 failed, 24 passed
```

The real RED was limited to the missing exact product copy and heading. The API
schema, speaker labels, access/share separation and no-email checks were already
green. The minimal implementation added the required heading and helper copy
to the existing server-owned calendar-context renderer. The existing
`{{ calendar_context }}` slot in `meeting_detail_content.html` carries the same
component on both routes, so no duplicate template branch was introduced.

Final receipts:

```text
focused calendar-roster cases: 3 passed, 22 deselected, 1 warning in 3.12s
full contract/detail slice: 25 passed, 1 warning in 19.65s
```

## Zero-Side-Effect Receipt

Each integration scenario linked a real meeting to a synthetic event with 25
roster entries. The accepted state after linking was:

| Observable | Accepted result |
| --- | --- |
| Meeting visibility | remains `owner_only` |
| Workspace memberships | unchanged |
| Unauthorized attendee view | `404 meeting_not_found` |
| Share grants | `0` before and after |
| Egress audit events | `0` before and after |
| Export packages | `0` before and after |
| Active share-panel grants | empty |
| Report/summary/message/email recipients | no recipient or delivery action created |
| Raw participant emails in API/review responses | `0` occurrences |
| Calendar-to-speaker assignments | `0`; transcript remains `SPEAKER_00`, `SPEAKER_01` |

`recipient_candidate_class` remains bounded roster metadata only. It does not
create an action field, grant, recipient, export or egress event.

## Requirement Reconciliation

| Requirement | Final schema/UI behavior | Receipt |
| --- | --- | --- |
| FR-020 | `CalendarRosterReviewState` is projected only inside the already-authorized meeting review. | Owner review sees the safe roster; the synthetic attendee receives privacy-safe 404. |
| FR-021 | Roster data is independent of membership, visibility, `access`, `share`, recipients and delivery stores. | Both 25-participant cases retain zero grants/egress/exports and unchanged membership/visibility. |
| FR-022 | Calendar names never rename transcript or diarization labels. | Unit, contract and rendered review retain `SPEAKER_00`/`SPEAKER_01`; injected speaker hints are discarded. |
| FR-023 | Speaker-name suggestions remain a separate future capability. | `future-speaker-naming.md` and the product deferred-work register require consent, confidence, correction, speaker truth, privacy and authorization evidence. |
| FR-024 | Recurring context still requires the same hashed series and workspace/space. | US5 predecessor query remains unchanged by the roster projection. |
| FR-025 | Previous recurring context still receives its own meeting-access decision. | US5 owner/team and denied predecessor receipts remain unchanged. |
| FR-026 | Missing, deleted, ambiguous or inaccessible predecessors remain absent without fallback or leak. | US5 null/no-placeholder behavior remains unchanged; US6 introduces no alternate projection. |
| FR-040 | People, rooms, resources and groups remain invited roster metadata, not attendance or speaker claims. | Bounded participant kinds plus exact invitee-not-speaker copy on both surfaces. |
| FR-044 | Calendar context is structurally separate from transcript and speaker panels. | Web and embedded render tests prove roster names occur only in the calendar-context section and `SPEAKER_XX` only in recording/speaker panels. |
| FR-045 | The optional recurring pointer does not mutate title, roster or speaker labels. | US5 pointer and US6 roster/speaker regression suites pass together without state mutation. |

No identity/permission conflict remains in the final schemas or UI. The roster
models use `extra="forbid"`; safe display metadata is bounded, raw email is not
projected, and speaker/access/share models remain separate fields in
`MeetingReviewResponse`.

## Final US6 Regression Receipt

The final six-file server slice covered normalization, review projection,
access denial, share/delivery stores, API schema separation and web/embedded
rendering:

```sh
cd apps/server
uv run pytest -q \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_calendar_participants.py \
  tests/integration/test_calendar_access_policy.py \
  tests/integration/test_meeting_share_links.py \
  tests/contract/test_cabinet_contract.py \
  tests/integration/test_cabinet_meeting_detail.py
```

Accepted result:

```text
74 passed, 1 existing StarletteDeprecationWarning in 26.09s
```

Focused Ruff covered the production renderer and all six US6 test files:

```text
7 files already formatted
All checks passed!
```

`git diff --check` returned clean.

## US6 Exit Decision

- Authorized roster context only: PASS.
- Calendar names remain separate from speaker truth: PASS.
- Zero permission/share/recipient/delivery effects: PASS.
- Exact invitee-not-speaker copy on browser and embedded routes: PASS.
- Future speaker naming explicitly deferred: PASS.
- Recurring-context authorization and no-leak invariants preserved: PASS.

US6 is complete and ready for feature-level validation. Commit, PR, release and
deployment remain outside this story checkpoint.
