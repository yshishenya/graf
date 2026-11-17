# Quickstart: MVP Live Owner Journey And UI Proof

Run from the repository root. The active T020 continuation is a repair of the
metadata probe. Historical June validation receipts remain historical; this
guide does not authorize repeating their old app, signing or deployment path.

## 1. Active context and gates

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected: F052 from the owned ignored `.specify/feature.json`; root AGENTS.md
stays stable. Read the current spec/plan/contracts/tasks and project guidance.
Before code, independent requirements checklists must pass, read-only analyze
must meet the zero critical/high threshold, and existing T020/#1819 mapping
must be reconciled without a duplicate issue. A STOP is not implementation
permission. Requirement-quality approval is separate from actual acceptance.

## 2. Focused offline T020 regression

After the implementation gate opens, add the regression first, reproduce the
false pass, then repair the existing probe and rerun:

```sh
python3 -m unittest discover \
  -s specs/052-mvp-live-ui-proof/evidence \
  -p 'test_production_owner_journey_probe.py' -v
```

Expected: all owner-contract negative/positive/type/access/category/count,
request/configuration/health/aggregate/exit/privacy cases pass. Tests must
also reject missing/malformed/different response meeting IDs and accept equal
normalized UUIDs without printing either ID. This focused command is separate
from GitHub's diff-based test selection; retain its actual source identity.
Import must
not invoke main; request functions/environment are patched with synthetic
values. No network, real session, real meeting, app, database, mail, payment,
provider or dependency installation. This establishes tool regression only.

## 3. Production candidate metadata — separate actual acceptance

Only with an authorized current candidate and runtime owner context:

```sh
python3 specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py
```

Expected: bounded metadata under
`contracts/owner-journey-proof-contract.md`. No input values or response content
are printed. Without both owner inputs the result is blocked and exit1, even
when health is green. Exit0 means healthy requests and positive scoped API
metadata; `owner_journey_status` remains unproven. This is an intentional
change from the old health-only exit0 behavior. Real observed states/counts
must be recorded before T020 can complete; tests and merge do not replace them.

## 4. Web/embedded UI acceptance — separate from API metadata

Use the existing `evidence/browser-runtime-check.cjs` for its fixture runtime
scope only. Actual owner acceptance must inspect the current authenticated
web desktop/compact and embedded review of the same fresh candidate: playback,
working timestamp seek, visible speaker activity lanes, transcript, outcomes,
auth/unavailable states, keyboard/focus/accessibility and absence of critical
layout/false-ready findings. Local fixtures cannot prove production/UI use.
Reference observations include assignment affordances, label/row/lane
association and multiple-speaker distinguishability under the interface
contract. Observe existing permitted GRAF interactions without adding editing
or changing real meeting data; unavailable editing remains explicitly outside
the implemented scope.
The API interval/seek counters prove neither visible lanes nor working seek.

## 5. Native checks

The probe-only repair does not change native code. Do not run native builds or
suites without an applicable change/new reason; required GitHub macos-pr still
selects the exact diff under project policy. If native code is later needed,
classify/read its full dependencies and use its focused tests first.

## 6. Single local application

Before any app build, launch or manual/end-to-end acceptance, read
`docs/agent-guidance/local-development.md` and follow the existing dev-harness
for `/Applications/GRAF Dev.app` only. Check availability, source/version,
signing and occupancy; unknown occupancy blocks updates/restarts/UI mutation.
Do not launch another bundle or executable, bypass a lock or disturb a recording.
Local Dev proof does not establish notarized public distribution acceptance.

## 7. Reference review

Follow Constitution VII, PRD §§29–30 and the interface contract: reference
fidelity, documented trust/accessibility/localization/defect deviations,
independent code and asset rights. Functional wording may match literally.
Private screenshots/content stay outside git; extracted assets are forbidden.
No reference UI inspection is required merely to repair the metadata probe.

## 8. PR validation

After focused validation and convergence, record lane, exact SHA, checked base,
review and limits. Write `changes/unreleased/F52.yaml`; root CHANGELOG.md is
reserved for the release operator. Required GitHub checks are governance-fast,
macos-pr and pr-metadata on the exact final PR head and checked base. Use:

```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <number>
```

Review unresolved comments and verify the normal linear merge. No local full
suite or repeated historical checks are required without a new reason; local
ci-local.sh --fast/--full is diagnostic, never authoritative release evidence.

## 9. Release gate

A release is separate: latest published GitHub Release, reviewed/merged exact
source, operator-assembled changelog, immutable frozen candidate and one
successful authoritative GitHub release-full for that candidate, immutable go
decision, tag and Russian GitHub Release. Follow release-and-validation.md;
health or the metadata probe alone cannot pass this gate.

## 10. Deployment gate

Only in an approved release operation after its gates, use the documented CD
dry-run and candidate/authoritative-evidence execute sequence from
`docs/agent-guidance/release-and-validation.md`. Preserve backup, migration,
rollback, health and smoke requirements. Do not deploy or restart a service to
repair/run an offline evidence tool.

## 11. Evidence privacy and closeout

Review the diff and scan new evidence for real cookies, tokens, account IDs,
signed URLs, private paths, raw audio, transcript/generated text and private
meeting titles. Fixed artificial regression sentinels and policy literals must
be distinguishable from real data; stdout/error tests must reject sentinels.
Retain metadata logs, checksums and version links outside heavy build folders.
T019/T020 stay open until original live criteria pass. Closing any issue still
requires its detailed Russian closeout, stock validate-issue-closeout.py
--verify-live, and actual final-state verification. No closeout is performed by
this offline quickstart.
