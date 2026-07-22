# Feature 121 GitHub issue mapping

Generated and resynchronized by `$speckit-taskstoissues`. Constitution v4.0.0
now requires complete plaintext model-call content in Langfuse and the retained
Generation Call ledger plus the complete plaintext canonical transcript in
Temporal History, without GRAF-managed observability deletion.
Affected issue bodies were resynchronized after the clean repeated analysis;
`tasks.md` remains the implementation source of truth.

## Reconciliation status

- Planning tasks T001-T005 and 87 implementation/validation tasks are complete.
  Post-implementation analyze finished at CRITICAL/HIGH/MEDIUM/LOW `0/0/0/0`;
  canonical CI, repeated correctness/security review, and final Ponytail
  `Lean already. Ship.` evidence are recorded in `quickstart.md`.
- T050/#4170, T057/#4177, and T089/#4209 remain open. They require the owner's
  LiteLLM URL/key, immutable synthetic manifests, a real two-worker forced-crash
  GEPA exercise, and live Generation Call/Temporal/Langfuse three-store
  read-back. Runtime flags remain off; no unavailable evidence is claimed.
- Every implementation and validation task T006-T095 has exactly one canonical
  Russian issue in
  [feature:121](https://github.com/yshishenya/crisp/issues?q=is%3Aissue%20label%3Afeature%3A121).
- The mapping is contiguous: T006 maps to
  [#4126](https://github.com/yshishenya/crisp/issues/4126), T007 maps to #4127,
  and so on through T095, which maps to
  [#4215](https://github.com/yshishenya/crisp/issues/4215). Equivalently,
  `issue number = numeric task id + 4120`.
- The post-implementation mandatory repository-wide validator passed all 149
  current Spec Kit issues. Completed Feature-121 issues receive their detailed
  Russian closure receipt after the implementation PR is merged; the three live
  gates remain open and are linked from the release notes.
- With explicit user approval,
  [feature 119 issue #3992](https://github.com/yshishenya/crisp/issues/3992)
  was normalized without changing its task scope. The mandatory
  repository-wide canon validator then passed for all 136 open Spec Kit issues.

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
