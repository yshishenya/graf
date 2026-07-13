# Feature 098 Ponytail Review

**Recorded**: 2026-07-13 (Europe/Moscow)
**Task**: T099
**Lane**: high-risk active Spec Kit slice
**Reference**: `docs/agent-guidance/ponytail-upstream.md`

## Final Verdict

**Clean for pre-commit PR readiness with two explicit bounded debt ceilings.**

The first exact-diff review was not clean. It found one high-priority privacy
boundary defect, three medium simplification/retention/test-quality findings,
one low consolidation opportunity and two unmarked intentional debt points.
The final diff remediates every high/medium item and marks both debt ceilings.

## Finding Reconciliation

| Initial finding | Resolution | Evidence |
|---|---|---|
| P1: calendar titles and roster display names could carry URL/email/secret-like text into match/context/cabinet; calendar title application bypassed ingest policy | Added one pure shared `domain/metadata_text.py` policy and reused it in calendar normalization, matcher, meeting-title application, context/roster projections and cabinet title/roster egress. Unsafe title becomes `policy_hidden`; unsafe display name becomes absent. | Unit normalization/matcher/cabinet tests plus `72` privacy/forbidden-content acceptance tests |
| P2: consumed match attempt duplicated the full sensitive snapshot already copied into authoritative context | Added one shared `scrub_match_attempt_snapshot()` used immediately after successful consume and by disconnect lifecycle. State/reason/consumption correlation remains; candidate/event/title/roster/time/fingerprint content is cleared. | `test_us1_clear_match_consumes_atomically_and_preserves_safe_title_roster_idempotency` |
| P2: macOS queue persisted dead `calendarMatchDecisionIntent` that create transport never reads | Removed the field, coding key, queue parameter, merge state and retry assertions. Server attempt is the sole durable intent owner; queue retains only opaque attempt and selected event IDs. Unknown legacy JSON fields remain backward-safe under `Codable`. | `195` focused Swift tests; encoded queue explicitly omits the field |
| P2: 098 Swift receipts inspected source strings rather than behavior | Replaced intent/order/release assertions with direct prompt closures and a small pure `DesktopCalendarResolvePolicy` seam used by the app. Kept only existing static UI-wiring checks where SwiftUI behavior is not exposed as a cheap runtime seam. | CalendarAutoContextMatch, Reminder and CaptureControl tests in the `195`-test slice |
| P3: duplicated Python state/reason/title-source sets | Deferred. Centralizing all existing enums in this high-risk diff would touch unrelated consumers and migrations without fixing a current defect. Trigger: add a shared typed registry when another consumer or another state is introduced, or when drift is observed by contract tests. | Existing contract drift/RLS/audit tests remain green |

## Explicit Debt Ceilings

- `calendar/lifecycle.py` keeps source disconnect as a workspace-bounded scan.
  A `ponytail:` comment sets the upgrade trigger at observed latency/row volume
  that justifies indexed source-reference columns.
- Migration `0021` downgrade is intentionally lossy because schema 0020 cannot
  represent 098-only no-link/clear/delete rows. A `ponytail:` comment requires
  pre-migration backup/export and sets the trigger for a reversible side table
  only if production rollback of 098 becomes a supported operation.

## Simplification Checks

- No new runtime dependency was added; shared policy uses Python stdlib.
- No provider call, worker, cache, frontend app or native duplicate review UI
  was introduced.
- Existing server-owned cabinet components, CSS variables, routes and embedded
  navigation remain the product surface.
- The pure Swift seam is a small value/policy pair, not a coordinator framework.
- Attempt scrub reuses one helper instead of duplicating lifecycle mutation.

## Validation

- Focused server: `145 + 99 + 162` passed.
- Focused macOS: `195` passed.
- Privacy/forbidden-content: `72` passed.
- Ruff: all checks passed.
- Diff whitespace: clean.

This review does not claim completion of the separately deferred Codex Security
scan.
