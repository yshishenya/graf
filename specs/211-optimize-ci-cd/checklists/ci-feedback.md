# CI feedback requirements checklist — A1

Created: 2026-09-09. Scope: US5, FR-015–FR-018, SC-010–SC-011.
Owner of marks: independent requirements reviewer, not implementation author.
Old requirements/operational/fast-lane checklists are historical; their marks do not approve A1.

- [x] CHK001 Are head/base identity, actual merge-base selection and receipt consistency defined for both PR and merge_group? [Completeness, Spec FR-015, US5.1]
- [x] CHK002 Are missing, malformed and unavailable event bases required to fail before tests, without default-base substitution or successful receipt? [Failure coverage, Spec FR-015, US5.2]
- [x] CHK003 Is manual dispatch explicitly diagnostic, with null event base and no implied PR/MG provenance? [Clarity, Spec FR-015, US5.3]
- [x] CHK004 Are the unchanged lint/compile scope, single execution, ordering and fail-fast outcomes measurable for fast/full and every selected server test stage? [Measurability, Spec FR-016, SC-010]
- [x] CHK005 Do the requirements consistently distinguish local focused, mandatory GitHub fast and diagnostic local wide runs, and require active guidance to agree without weakening release/security/RLS gates? [Consistency, Spec FR-008, FR-010, FR-017]
- [x] CHK006 Does A1 explicitly preserve check names, events, permissions, concurrency and closeout trust, with a gap-free separately authorized metadata migration? [Boundaries, Spec FR-018, Plan Deferred migration]
- [x] CHK007 Are historical full-inside-execute evidence/approvals separated from current GitHub evidence reuse and current authorization? [Consistency, Spec Clarifications, FR-005–FR-006, Plan Authority]
- [x] CHK008 Are acceptance and reporting honest about deferred edited reruns, unrun GitHub/full/release gates and the absence of a new timing/token benchmark? [Evidence, Spec SC-010–SC-011, Plan Validation]

## Review record

**Result**: PASS for A1 requirements quality, 2026-09-09.
**Reviewer**: independent Codex agent `/root/graf_requirements_review`, explicitly authorized by the user. The reviewer did not write the implementation, spec, plan or tasks.
**Blocking findings**: CRITICAL 0, HIGH 0 for this bounded requirements review.

- CHK001–CHK003: [spec.md](../spec.md), US5 scenarios 1–3 and FR-015; [plan.md](../plan.md), A1 design 1–2; [data-model.md](../data-model.md), event-base identity. The contract binds the actual merge-base input to receipt identity, explicitly rejects unavailable event bases, and keeps manual dispatch diagnostic. Local unknown-diff fallback is not authorization to substitute an unavailable PR/MG base.
- CHK004: [spec.md](../spec.md), US5.4/FR-016/SC-010; [plan.md](../plan.md), A1 design 3; [quickstart.md](../quickstart.md), A1 acceptance. Tests must demonstrate both ordering and non-execution after either static failure; no reduction in the selected test set is authorized.
- CHK005: [spec.md](../spec.md), FR-008/FR-010/FR-017; [plan.md](../plan.md), A1 design 4; [contracts/ci-cd-cli.md](../contracts/ci-cd-cli.md), documentation consistency. CHK005 wording was clarified to assess the requirements rather than falsely assert that unchanged active guidance already conforms. Conformance remains implementation work.
- CHK006: [spec.md](../spec.md), FR-018; [plan.md](../plan.md), deferred metadata-check migration. A1 leaves the combined required gate intact. Future removal of duplicate checks requires a separate reviewed migration and confirmed live protection; this review does not approve that future design or a live settings change.
- CHK007: [spec.md](../spec.md), current status, clarification session and FR-005–FR-006; [plan.md](../plan.md) and [research.md](../research.md), explicit historical boundaries; [quickstart.md](../quickstart.md), production exclusion. Historical approvals and local diagnostic runs cannot authorize release.
- CHK008: [spec.md](../spec.md), SC-010–SC-011; [quickstart.md](../quickstart.md), A1 acceptance. PR-body reruns remain unresolved, no new timing/token benchmark is claimed, and GitHub/full/release evidence is explicitly outside this local package.

Reviewed the current workflow, real runner selection and existing evidence/closeout consumers independently before evaluating these requirements. The previously reported event-base mismatch is addressed by FR-015; metadata splitting is safely excluded from A1.

These marks approve requirements only. They do not attest code correctness, test results, task review, issue sync, clean analyze, merge readiness or release readiness. Tasks and analyze remain separate gates before implementation. Existing historical checklist marks were not changed.
