# Feature 098 US4 Stable Title And Context History Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Tasks**: T064-T074
**Requirement trace**: FR-016-FR-019, FR-027, FR-029-FR-030,
FR-035-FR-039, FR-041-FR-042, FR-052; SC-006-SC-007, SC-010,
SC-014

## Result

US4 is ready. A match copies safe title, time, roster, series and source
fingerprints into the single meeting-owned context row. Later provider rename,
move, deletion, cancellation or roster replacement cannot rewrite that history.
Authoritative titles remain authoritative, a calendar correction may replace a
calendar title, and clear removes the relationship/roster while leaving the
already visible title stable.

Expired and source-bound unresolved attempts now purge at their lifecycle
boundary. Source disconnect detaches provider snapshots while retaining only
the safe meeting-owned match snapshot. Meeting deletion scrubs context and
consumed-attempt content, adds an explicit `calendar_context` artifact to the
deletion report and preserves transaction rollback truth.

The standalone Codex Security scan remains separately deferred by explicit
user instruction. It was not resumed, completed, failed or counted as US4
evidence. The authorization, lifecycle and metadata-only checks below are
ordinary feature acceptance tests only.

## Test-First Receipts

### Title precedence and clear

The pre-change T064 baseline was:

```text
6 passed
```

The 16 new title-source, correction, clear and ingest-provenance scenarios were
green immediately:

```text
16 passed, 22 deselected
```

This is recorded as pre-existing US3/foundational behavior, not represented as
a fabricated RED. It proved that `app_context`/`generic` are replaceable;
`user_confirmed`, `upload_provided`, `file_name_derived` and `legacy_unknown`
are authoritative; calendar-to-calendar correction is allowed; clear keeps the
latest visible calendar title; and an exact create retry does not reattach a
cleared context.

The broader persistence baseline exposed two existing-contract mismatches:

- an ended event could be explicitly linked to a later recording;
- an old assertion still expected the retired compatibility value
  `user_or_generic` instead of canonical `legacy_unknown`.

The first received a bounded end-time guard in the explicit selection path.
The stale assertion was reconciled to the documented title provenance model.

### Provider mutation stability

The new five-way provider mutation matrix initially produced:

```text
4 failed, 1 passed
```

Rename, move, cancel and roster-sync reached SQLAlchemy's default in-session
`evaluate` synchronization and compared offset-naive database values with
offset-aware sync instants. Provider deletion was already fully green and
proved that immutable meeting title/context remained stable.

The sync update now uses database-backed `fetch` synchronization. This avoids
the timezone comparison and keeps the loaded provider row truthful after the
bulk update. Final targeted result:

```text
5 passed, 1 existing StarletteDeprecationWarning in 3.32s
```

### Deletion and disconnect lifecycle

The pre-change three-file lifecycle baseline was:

```text
8 passed, 1 existing StarletteDeprecationWarning in 8.42s
```

The six new lifecycle scenarios then produced:

```text
5 failed, 1 passed, 8 deselected
```

The RED failures proved that meeting deletion retained live context snapshots
and consumed-attempt content, source disconnect retained unresolved attempts
and provider-event links, and the deletion report omitted a
`calendar_context` artifact. The already-green test proved transaction rollback
on deletion failure.

An additional exact-TTL receipt was added while implementing the lifecycle
path. The final new-scenario result is:

```text
7 passed, 8 deselected, 1 existing StarletteDeprecationWarning in 3.78s
```

### Metadata-only activity

The correction/clear review assertion first failed with no calendar activity
items. After the bounded projection was added, the same test passed with two
`calendar_context_owner_mutation` items whose only reasons are
`user_selected` and `user_cleared`, whose outcome is `completed`, and whose
artifact class is empty. A deletion lifecycle receipt separately proves the
safe `calendar_context_deletion_accounted` / `meeting_deleted` projection.

No event title, roster value, provider ID, URL, passcode or raw payload is
copied into activity data.

## Stable Snapshot And Review Truth

The provider mutation matrix proves all of the following across rename, move,
delete, cancel and roster replacement:

- meeting title and `title_source` stay unchanged;
- matched start/end instants stay unchanged;
- safe matched title and title state stay unchanged;
- roster values/state/count stay unchanged;
- series and source-version fingerprints stay unchanged;
- the cabinet review projection is identical before and after provider sync;
- mutable provider participant/title values do not appear in review output.

New 098 rows are always read from the immutable context snapshot. The only live
participant fallback remains intentionally limited to `legacy_linked` rows that
predate the snapshot contract.

## Source Disconnect And Attempt TTL

The accepted lifecycle behavior is:

- an unconsumed attempt is purgeable when `expires_at <= cutoff`, including
  exact equality;
- an unconsumed attempt referencing a disconnected source is deleted;
- unresolved context candidate IDs from that source are removed;
- an ambiguity with no remaining candidate becomes `calendar_unavailable`
  rather than silently selecting or fabricating a match;
- consumed attempts retain only minimal correlation state after disconnect;
- a matched context detaches its live provider-event FK but keeps its immutable
  safe title/time/roster/series/source snapshot;
- future provider event, participant, conference-link and reminder cache rows
  are purged under the existing disconnect transaction;
- credentials and selected calendars keep the existing disconnected/purged
  truth.

## Meeting Deletion And Rollback

Meeting deletion now moves any authoritative context row to `deleted`, removes
event/attempt FKs and candidate IDs, and scrubs matched time, title, roster,
series and source-version snapshot fields. Consumed match attempts for the
meeting are purged after their context FK is detached.

The deletion report contains exactly one controlled `calendar_context` row. It
is `purged` when derived context existed and `not_applicable` otherwise. The
existing generic deletion-report projector already accepted the new safe
artifact class, so no redundant special-case rendering or report code was
introduced.

The failure-path receipt injects an unavailable storage implementation after
calendar accounting starts. The request returns the existing safe 503 and the
transaction restores the original meeting, request/report rows, artifact list
and calendar context. Calendar cleanup is therefore atomic with normal meeting
deletion accounting.

## Migration, Cabinet And Clear Copy

The existing portable `0021` migration already implemented deterministic
legacy multi-link collapse, safe title/time backfill, cleared/deleted tombstone
reconciliation, SQLite downgrade and RLS declarations. Its final focused
receipt is:

```text
4 passed, 1 existing StarletteDeprecationWarning in 1.24s
```

The cabinet continues to reuse the immutable roster snapshot and the existing
GRAF context/activity primitives. The stable-title confirmation remains exact:

```text
Контекст будет убран, а название записи останется прежним.
```

Browser/embedded parity, localized state copy and the clear workflow produced:

```text
3 passed, 1 existing StarletteDeprecationWarning in 1.05s
```

No new visual language, route family or native duplicate review surface was
introduced.

## Final US4 Regression Receipt

The final eight-file integration slice was split only to preserve complete
terminal receipts:

```text
63 passed, 1 existing StarletteDeprecationWarning in 19.71s
28 passed, 1 existing StarletteDeprecationWarning in 25.46s
```

Combined:

```text
91 passed, 0 failed
```

It covers title precedence, correction/clear/retry, provider mutation,
migration reconciliation, context/attempt lifecycle, deletion rollback,
deletion reporting and cabinet detail behavior.

Focused Ruff covered all changed US4 production and test files:

```text
All checks passed!
```

Ruff formatting reported all focused files already formatted after the
mechanical pass. `git diff --check` also returned clean.

## US4 Exit Decision

- Authoritative title provenance and calendar correction precedence: PASS.
- Stable title on clear and exact create retry: PASS.
- Provider rename/move/delete/cancel/roster stability: PASS.
- Immutable review/list snapshot with legacy-only fallback: PASS.
- Exact-TTL and disconnected-source attempt purge: PASS.
- Unresolved candidate scrub without retrospective match: PASS.
- Meeting deletion snapshot scrub and explicit artifact accounting: PASS.
- Atomic rollback on deletion failure: PASS.
- Metadata-only correction/clear/deletion activity: PASS.
- Portable legacy reconciliation and cabinet clear copy: PASS.
- Deferred standalone security audit: unchanged and not represented as done.

US4 may exit to recurring meeting continuity.
