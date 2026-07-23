# Feature 121 GitHub issue mapping

Generated and resynchronized by `$speckit-taskstoissues`. Constitution v4.0.0
now requires complete plaintext model-call content in Langfuse and the retained
Generation Call ledger plus the complete plaintext canonical transcript in
Temporal History, without GRAF-managed observability deletion.
Affected issue bodies were resynchronized after the clean repeated analysis;
`tasks.md` remains the implementation source of truth.

## Reconciliation status

- Planning tasks T001-T005 and 91 implementation/validation tasks are complete.
  Post-implementation analyze finished at CRITICAL/HIGH/MEDIUM/LOW `0/0/0/0`;
  canonical CI, repeated correctness/security review, and final Ponytail
  `Lean already. Ship.` evidence are recorded in `quickstart.md`.
- T050/#4170 and T089/#4209 have production LiteLLM, retained Generation Call,
  Temporal History, private Langfuse, reconciler, and zero-leak evidence.
  T057/#4177 is complete: owner-approved immutable synthetic manifests and the
  human-labelled calibration pack were read back from private production
  Langfuse; run `da6ac03b-470a-4612-87fb-4210bc646706` passed development and
  held-out gates, approval, promotion, and rollback; and run
  `b772ab2e-c021-4a33-8ce1-4796ba019197` proved two-worker forced-crash resume
  (worker `t057-worker-l` exit 137, checkpoint 1 → 5, activity attempt 2) before
  correctly failing closed on a 0.83 held-out score. Both traces and Temporal
  histories retain complete plaintext content; the receipt contains hashes,
  sizes, and counts only.
- Every implementation and validation task T006-T096 has exactly one canonical
  Russian issue in
  [feature:121](https://github.com/yshishenya/crisp/issues?q=is%3Aissue%20label%3Afeature%3A121).
- The mapping is contiguous: T006 maps to
  [#4126](https://github.com/yshishenya/crisp/issues/4126), T007 maps to #4127,
  and so on through T095, which maps to
  [#4215](https://github.com/yshishenya/crisp/issues/4215). Equivalently,
  `issue number = numeric task id + 4120`.
- After merge, production deploy, public
  [`v2026.07.23.3`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.3),
  installed-app verification, and the production AI observability closeout,
  91 completed issues have verified evidence. No Feature-121 issue remains open;
  T096/#4253 is closed after the accepted outcome pointer hotfix was deployed and
  verified.
- Implementation/release links: PR
  [#4235](https://github.com/yshishenya/crisp/pull/4235), native purge hotfix
  [#4242](https://github.com/yshishenya/crisp/pull/4242), release prep
  [#4243](https://github.com/yshishenya/crisp/pull/4243), response-attempt
  reconciler [#4250](https://github.com/yshishenya/crisp/pull/4250), and
  accepted-summary pointer hotfix [#4277](https://github.com/yshishenya/crisp/pull/4277),
  T057 operations [#4281](https://github.com/yshishenya/crisp/pull/4281),
  retry fix [#4282](https://github.com/yshishenya/crisp/pull/4282),
  judge normalization [#4283](https://github.com/yshishenya/crisp/pull/4283),
  live receipt [#4284](https://github.com/yshishenya/crisp/pull/4284), and
  release prep [#4285](https://github.com/yshishenya/crisp/pull/4285).
  Release `v2026.07.23.3` carries the production closeout. The
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
| T096 | #4253 | Accepted-summary pointer production regression hotfix |

Issues must only be closed after their acceptance criteria and evidence are
verified. Matching task checkboxes must only be marked complete after the same
verification.
