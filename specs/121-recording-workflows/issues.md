# Feature 121 GitHub issue mapping

Generated and resynchronized by `$speckit-taskstoissues`. Constitution v4.0.0
now requires complete plaintext model-call content in Langfuse and the retained
Generation Call ledger plus the complete plaintext canonical transcript in
Temporal History, without GRAF-managed observability deletion.
Affected issue bodies were resynchronized after the clean repeated analysis;
`tasks.md` remains the implementation source of truth.

## Reconciliation status

- Planning tasks T001-T005 and 89 implementation/validation tasks are complete.
  Post-implementation analyze finished at CRITICAL/HIGH/MEDIUM/LOW `0/0/0/0`;
  canonical CI, repeated correctness/security review, and final Ponytail
  `Lean already. Ship.` evidence are recorded in `quickstart.md`.
- T050/#4170 and T089/#4209 have production LiteLLM, retained Generation Call,
  Temporal History, private Langfuse, reconciler, and zero-leak evidence. Only
  T057/#4177 remains open: it still requires owner-approved immutable synthetic
  manifests, a human-labelled calibration pack, and a real two-worker
  forced-crash GEPA promotion/rollback exercise.
- Every implementation and validation task T006-T095 has exactly one canonical
  Russian issue in
  [feature:121](https://github.com/yshishenya/crisp/issues?q=is%3Aissue%20label%3Afeature%3A121).
- The mapping is contiguous: T006 maps to
  [#4126](https://github.com/yshishenya/crisp/issues/4126), T007 maps to #4127,
  and so on through T095, which maps to
  [#4215](https://github.com/yshishenya/crisp/issues/4215). Equivalently,
  `issue number = numeric task id + 4120`.
- After merge, production deploy, public
  [`v2026.07.22.4`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.22.4),
  installed-app verification, and the production AI observability closeout,
  89 completed issues have verified evidence. Exactly 1 of 90 remains open:
  #4177.
- Implementation/release links: PR
  [#4235](https://github.com/yshishenya/crisp/pull/4235), native purge hotfix
  [#4242](https://github.com/yshishenya/crisp/pull/4242), release prep
  [#4243](https://github.com/yshishenya/crisp/pull/4243), and response-attempt
  reconciler [#4250](https://github.com/yshishenya/crisp/pull/4250). The
  repository-wide issue-canon validator is rerun after tracker closeout.

## Phase ranges

| Tasks | GitHub issues | Scope |
|---|---|---|
| T006-T014 | #4126-#4134 | Foundational data, policy, and lifecycle |
| T015-T021 | #4135-#4141 | Trustworthy recording start |
| T022-T030 | #4142-#4150 | Active recording control and recovery |
| T031-T034 | #4151-#4154 | Custody, upload, and processing |
| T035-T038 | #4155-#4158 | Meeting review workspace |
| T039-T057 | #4159-#4177 | Templates, Langfuse, LiteLLM, Temporal, and GEPA |
| T058-T071 | #4178-#4191 | Sharing and invitations |
| T072-T079 | #4192-#4199 | Export and deletion |
| T080-T086 | #4200-#4206 | Accessibility and Russian cross-surface UX |
| T087-T095 | #4207-#4215 | Validation, review, and release boundary |

Issues must only be closed after their acceptance criteria and evidence are
verified. Matching task checkboxes must only be marked complete after the same
verification.
