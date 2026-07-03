# Refactor Batch Contract

Every future implementation PR derived from 086 must include these fields in
its PR description or linked task.

| Field | Required Content |
|-------|------------------|
| Batch id | Stable id such as `RB-086-01` |
| Classification | `delete now`, `split soon`, `keep intentionally`, or `risky / needs spec` |
| Included paths | Exact files/directories touched |
| Excluded surfaces | Behavior or paths intentionally out of scope |
| Runtime flow | Which upload-custody stage is affected |
| Expected diff shape | Move-only, extraction-only, deletion-only, contract update, or test-only |
| Required checks | Exact commands or focused validations |
| Stop condition | What observation stops or reverts the PR |
| Evidence source | Static search, runtime entrypoint, test, or contract evidence |

## Batch Rules

- One responsibility boundary per PR.
- No combined desktop and server behavior change unless the batch is explicitly
  a contract slice.
- No deletion without caller, runtime, entrypoint, validation, and rollback
  evidence.
- No production deploy as part of 086-derived refactor PRs unless a separate
  release/deploy lane requests it.
