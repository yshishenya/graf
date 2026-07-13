# Feature 098 Implementation Evidence

**Recorded**: 2026-07-13 (Europe/Moscow)
**Validation lane**: high-risk active Spec Kit slice
**Branch**: `codex/098-calendar-auto-context-match`
**Current base / origin master**: `3b62270c2b6c8e236444d521759b682323aa80bf`
**State**: validated implementation committed at
`13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb`; no PR yet

## Scope Boundary

This evidence covers ordinary feature validation for automatic calendar context,
authorization, privacy-safe metadata projections, migration portability, macOS
prompt/queue behavior and fail-soft recording/upload behavior. It does **not**
run or complete the separately deferred feature 097 / Codex Security scan. No
production deploy, production migration, runtime smoke or installed-app release
proof is claimed here.

## Focused Server Gate — T091

The exact commands are the three server commands in `quickstart.md`, including
the final normalization, roster, cabinet-shell, cabinet-contract, CSRF,
provider-mutation, ingest and deletion receipts that were missing from the
earlier draft command set.

| Slice | Result |
|---|---|
| Unit and read-model | `145 passed`, `0 failed`, one existing Starlette warning, `0.31s` |
| API/OpenAPI/RLS contracts | `99 passed`, `0 failed`, one existing Starlette warning, `32.24s` |
| Integration matrix | `162 passed`, `0 failed`, one existing Starlette warning, `74.62s` |

The integration slice includes persisted provisional accept/reject, no
connected/selected calendar resolve-to-create, immediate consumed-attempt scrub,
post-match provider mutation stability and full provider-failure upload
continuity.

## Performance Receipt

Both measurements use the feature tests and synthetic data only.

| Operation | Samples / warm-up | Scale | Measured p95 | Limit |
|---|---:|---|---:|---:|
| Resolve | 100 / 10 | 4 selected sources, 50 candidate rows | `0.602250 ms` | `<= 200 ms` |
| Atomic consume | 100 / 1 | one attempt, meeting and context per sample | `2.007667 ms` | `<= 50 ms` |

The wrapper reruns passed `1/1` test in each case. The consume wrapper emitted
only `PytestAssertRewriteWarning` because the module was intentionally imported
before invoking pytest to print the otherwise internal measurement.

## Focused Ruff — T092

The exact `quickstart.md` Ruff command returned:

```text
All checks passed!
```

`git diff --check` is also clean on the final base.

## Focused macOS Gate — T093

Command:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CalendarAutoContextMatch|DesktopUploadClient|DesktopUploadQueue|DesktopCalendarReminder|CaptureControl|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Result:

```text
Build complete
195 tests, 0 failures in 0.700s (0.715s wall for selected tests)
```

The final macOS shape persists only the server-issued attempt ID and selected
event ID required by later transport. Decision intent remains durable on the
server attempt. Direct prompt-closure tests and the small pure
`DesktopCalendarResolvePolicy` seam prove automatic/selected/declined intent,
capture-first ordering and immediate upload processing without brittle
source-string inspection. A late resolve may enrich only a queue item whose
upload has not started; it cannot change the idempotent create identity after
upload begins.

## Migration / RLS — T094

The final focused SQLite/chain rerun returned:

```text
12 passed, 0 failed, one existing Starlette warning in 2.78s
```

The disposable PostgreSQL/RLS run and cleanup receipt is recorded in
`migration-evidence.md`: upgrade through `0021_calendar_auto_context_match`,
`rls_validation_result=pass`, `migration_verification_result=pass`, disposable
database cleanup and local stack cleanup all passed. The SQLite and disposable
PostgreSQL gates were both repeated after the final legacy-title backfill
hardening.

## Scenario / FR Matrix — T095

Every quickstart scenario is reconciled to an executable synthetic receipt in
`scenario-matrix.md`. The final suites include explicit coverage for
participants-only and link/location-only matching, exact 24-hour freshness and
expiry boundaries, strong duplicate identities, description-only non-signal,
persisted pre-start finalize/reject, no connected/selected calendars,
provider-mutation immutability, immediate attempt scrub and provider-failure
upload continuity.

## Requirement Checklists — T096

Both requirement-quality checklists remain complete after reading the final
spec, plan, research, data model, contracts, quickstart and validation files.
Their final reconciliation notes distinguish requirement quality from executed
implementation/release evidence.

## Changelog / Product Status — T097–T098

`CHANGELOG.md` keeps all 098 entries under `[Unreleased]`; none were moved into
the already published `2026.07.13.1` section during the base refresh.
`docs/current-product-status.md` states that 098 is locally implemented,
validated and committed, but not merged, released, deployed or
production-smoked.

The managed Spec Kit block in `AGENTS.md` was refreshed through
`$speckit-agent-context-update` to point at the 098 plan. Its first run found
PyYAML missing from the default interpreter; the successful retry reused the
existing server virtual environment and changed only the managed plan pointer.

## Ponytail Review — T099

`ponytail-review.md` records the initial non-clean findings and final
remediation. The final diff has one shared metadata-text policy, immediate
post-consume attempt scrub, no dead queue-level decision-intent field, direct
Swift behavior receipts and explicit ceilings/triggers for the two intentional
debt points. One low-priority enum-set consolidation is deferred because doing
it in this already high-risk diff would widen behavior without removing a
current bug.

## Final Diff Audit Recovery

The final pre-commit review found and closed additional correctness gaps before
the canonical rerun:

- chooser and matcher now use the same recently-ended guard, and dedupe keeps
  identical provider IDs from distinct external calendars separate;
- all ambiguity/correction labels and matched title/time projections pass the
  bounded safe-text policy, including legacy migration backfill;
- automatic matching still vetoes stale sources, while an explicit owner choice
  may select an otherwise-safe stale snapshot and keeps the stale audit class;
- correction candidates remain owner/workspace/source bounded, and non-owners
  receive the ordinary no-existence result;
- HTMX chooser focus lands on the chooser, while select/clear mutations return
  focus to the calendar-context heading;
- upload processing starts immediately after enqueue instead of waiting for a
  network resolve, and a late resolve cannot mutate a started upload's
  idempotent create identity.

The upload race and stale explicit-choice gaps were reproduced by failing tests
before their fixes. The final focused suites, disposable PostgreSQL/RLS gate and
canonical CI below include the corrected behavior.

## Authorization / Privacy / Forbidden Content — T100

Command scope:

```text
test_calendar_no_secret_content_egress.py
test_cabinet_no_secret_content_egress.py
test_calendar_access_policy.py
test_meeting_share_links.py
```

Result:

```text
72 passed, 0 failed, one existing Starlette warning in 13.37s
```

The shared policy rejects URL, email, token-like and control-character text at
calendar normalization, matching, meeting-title application and cabinet egress.
Roster snapshots expose only bounded display metadata and email presence; tests
prove zero attendee access/share/delivery/speaker side effects. These are
ordinary acceptance checks and are not represented as the deferred security
scan.

## Chrome Browser / Embedded Visual QA

The user selected Chrome and approved the browser pass. A loopback-only
synthetic fixture was exercised at the same default viewport through list,
matched, recurring, ambiguity, keyboard selection, correction, clear and
embedded desktop states. Real web and embedded mutations proved focus return
and durable `matched_user` / `cleared_by_user` state; eight inspected
screenshots and the exact state matrix are recorded in `visual-qa.md`.

The first list render exposed invalid nested anchors: Chrome moved the inner
`Выбрать` link into the row grid and pushed the date into a second implicit
row. The final implementation points the existing meeting-title link at the
chooser, keeps one valid link, preserves a fragment-free delete action and
uses the contract-required `64px` row minimum. The direct recovery slice passed
`3 passed`, `0 failed`, one existing Starlette warning in `1.85s`; the expanded
cabinet list/detail/contract slice then passed `85 passed`, `0 failed` in
`39.20s`. The server and browser pass were repeated from fresh synthetic state.

## Canonical Local CI — T101

The first closeout invocation ran on base SHA
`3b62270c2b6c8e236444d521759b682323aa80bf`. It passed the macOS build,
`629` Swift tests and `ContractValidation`, then exposed one server regression:
`test_meeting_create_reuses_one_initial_media_revision` received the generic
`idempotency_conflict` instead of the established `media_revision_conflict`.
The new request fingerprint included the revision identity and was evaluated
before the dedicated media-revision contract.

The remediation restored the dedicated revision/source conflict check before
generic fingerprint comparison. The direct recovery slice covering media
revision identity, ingest idempotency and calendar attempt consumption passed
`48 passed`, `0 failed`, one existing Starlette warning in `14.55s`.

One output-filter wrapper attempt then terminated before validation with exit
`141` because of an invalid local `awk` expression; no validation result is
claimed for that harness-only attempt. After the later final-diff audit fixed
the safe matched projection, correction focus, explicit stale-choice behavior
and the non-blocking upload race, the unchanged canonical script was run again
without a wrapper and completed successfully. It was repeated once more after
the Chrome-discovered list markup/layout correction; the table below is that
latest final-diff run:

| Canonical step | Final post-audit result |
|---|---|
| macOS legacy architecture guard | pass |
| macOS Swift build | pass |
| macOS Swift tests | `631 passed`, `0 failed` in `17.927s` (`17.981s` wall) |
| macOS contract validation | `ContractValidation: PASS` |
| Server tests | `1414 passed`, `4 skipped`, one existing Starlette warning in `351.01s` |
| Server Ruff | `All checks passed!` |
| Python compile | pass |
| Local RLS hardening boundary | expected non-live `blocked`, reason `postgres_test_database_required` |
| Production Compose rendering | pass |
| Deployment evidence scan | `pass`, `7` files |
| Final marker | `ci_local_result=pass`, wrapper exit `0` |

The local RLS boundary is deliberately non-live and does not substitute for a
database probe. The separate disposable PostgreSQL/RLS receipt was repeated
after the final migration hardening and passed upgrade through `0021`, direct
RLS validation, migration verification and cleanup.

## Task / GitHub Reconciliation — T102

The task-backed issue map is deterministic and complete: T001 maps to #3082,
and each subsequent task increments the issue number by one through T109 / #3190.
Baseline task-to-issue creation and canon validation recorded `109/109` with no
missing, extra or duplicate IDs. Phase 9 implementation issues are #3172–#3185;
release/deploy/cleanup issues #3186–#3190 remain pending and must not be closed
from local validation.

The final external-state recheck again returned `109` matching issues,
`T001–T109`, `109` open, `0` closed, no missing task IDs and no duplicates.
Superseding post-audit counts were posted to [T091 / #3172](https://github.com/yshishenya/crisp/issues/3172#issuecomment-4958233597),
[T093 / #3174](https://github.com/yshishenya/crisp/issues/3174#issuecomment-4958233798),
[T101 / #3182](https://github.com/yshishenya/crisp/issues/3182#issuecomment-4958233940)
and the pre-commit [T104 / #3185 approval gate](https://github.com/yshishenya/crisp/issues/3185#issuecomment-4958234102).

`tasks.md` now carries the exact completed-range issue/evidence map through
T104 / #3185. Earlier story receipts were already posted to #3082–#3171. Final
phase evidence comments were posted to #3172–#3184; #3185 contains the earlier
approval-gate state and receives the completed commit receipt during tracker
reconciliation. All issues remain open, there is no PR or remote feature
branch, and implementation commit
`13af76a7adacc4ee18f8dc4ff8f89d59b2df79cb` exists. Release tasks T105–T109 /
#3186–#3190 remain untouched.

T102 is complete as a reconciliation receipt, not as issue closure. Closing
comments remain a post-merge responsibility under T109.

## Known Limits / Remaining Gates

- Existing Starlette/httpx deprecation warning is unchanged and non-blocking.
- Canonical local CI has no PostgreSQL URL by design, so its RLS boundary reports
  `postgres_test_database_required`; the separate disposable PostgreSQL/RLS
  gate is the executable database receipt for this feature.
- Chrome browser/embedded visual QA passed with synthetic-only screenshots and
  real keyboard, choose and clear interactions. Responsive/mobile visual QA is
  outside this same-viewport 098 gate; existing responsive CSS remains covered
  by the cabinet contract tests.
- The standalone feature 097 security scan remains running/resumable and
  deliberately untouched.
- Implementation commit requires explicit user approval.
- PR review/merge, CalVer release, production migration/deploy/runtime smoke,
  installed-app evidence and issue closure remain later gates.
