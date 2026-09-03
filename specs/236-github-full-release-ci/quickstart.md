# Quickstart: Feature 236

## Local contract checks

```sh
python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml
python3 scripts/validate-full-ci-workflow.py --self-test
python3 scripts/check_spec_kit_governance.py
```

Run focused tests for the changed validator and CI contract. Run
`infra/scripts/ci-local.sh --fast` only for PR feedback; do not run local
`--full` as release evidence.

## GitHub candidate run

1. On a clean checkout of current `origin/master`, prepare and freeze a new
   candidate with `scripts/prepare-release.sh` and
   `infra/scripts/release-candidate.sh freeze`.
2. In GitHub Actions → **release-full**, enter the candidate ID and exact source
   SHA. Start it once; do not use the old cancelled candidate.
3. Confirm reservation, Ubuntu server job, macOS job and aggregate job all pass.
4. Download `graf-full-ci-<candidate-id>`, validate the evidence locally and
   bind it with `train-attest`/`decide`.

Expected result: one passed `authoritative_full=true` evidence record with no
skipped gates and every component SHA equal to the frozen candidate SHA.

## Closeout evidence

- Complete convergence, task checkbox updates and every other tracked feature
  change before merge, release preparation and candidate freeze.
- Record the final PR SHA in the PR description. Record the post-merge candidate
  SHA in immutable Full CI evidence, an ignored metadata-only closeout manifest
  and GitHub comments. Never write a post-freeze SHA back into tracked source.
- Validate each child issue #6416–#6429 with
  `python3 scripts/validate-issue-closeout.py --issue-json <issue.json>
  --tasks specs/236-github-full-release-ci/tasks.md --expected-sha
  <candidate-SHA>`; each comment must include the Russian closeout sections,
  task ID, PR number, the exact PR SHA with its successful `governance-fast`
  URL, and the exact candidate SHA with its successful `release-full` URL.
- Close umbrella #6415 only through a separate feature-level comment after all
  child issues are reconciled; it is not a task-backed `T000` row.
- The final manifest must show zero orphan or open task-backed child issues.

Reviewer-owned infrastructure checklist: `checklists/infra.md` records 9/9
requirements accepted, including create-once reservation, exact-SHA binding,
metadata-only evidence and separation of signing/deployment from GitHub CI.
