# Quickstart: Feature 236

## Local contract checks

```sh
python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml
python3 scripts/validate-full-ci-workflow.py --self-test
python3 scripts/check_spec_kit_governance.py
swift test --package-path apps/macos --filter 'CabinetBillingRuntimeTests|CabinetSidebarRuntimeTests|EmbeddedCabinetWebViewZoomTests'
sh apps/macos/Installer/Scripts/test-release-signing-custody.sh
swift test --package-path apps/macos --filter 'InstallerLifecycleEvidenceTests/testReleaseSigningFailureSimulationsStayFailClosed'
```

Run focused tests for the changed validator and CI contract. Run
`infra/scripts/ci-local.sh --fast` only for PR feedback; do not run local
`--full` as release evidence.

## GitHub candidate run

1. Resolve the latest published non-draft, non-prerelease GitHub Release and use
   its tag as the release-train base. On a clean checkout of current
   `origin/master`, prepare one new release with `scripts/prepare-release.sh`;
   prepared but unpublished changelog sections are folded into it.
2. Commit and merge release preparation, then freeze a new candidate with
   `infra/scripts/release-candidate.sh freeze`.
3. In GitHub Actions → **release-full**, enter the candidate ID and exact source
   SHA. Start it once; do not use the old cancelled candidate.
4. Confirm reservation, Ubuntu server job, macOS job and aggregate job all pass.
5. Download `graf-full-ci-<candidate-id>` and place its authoritative record at
   `.dev/ci-evidence/authoritative-<candidate-id>.json`. Validate that exact
   path, then bind it with `train-attest`/`decide`.

Expected result: one passed `authoritative_full=true` evidence record with no
skipped gates and every component SHA equal to the frozen candidate SHA.

## Closeout evidence

- Complete convergence, task checkbox updates and every other tracked feature
  change before merge, release preparation and candidate freeze.
- Record the final PR SHA in the PR description. Record the post-merge candidate
  SHA in immutable Full CI evidence, an ignored metadata-only closeout manifest
  and GitHub comments. Never write a post-freeze SHA back into tracked source.
- Keep T017 unchecked in the frozen candidate. After the GitHub Release,
  production deploy and installed-app checks complete, open a separate
  closeout-only PR from current `master` that changes T017 to `[X]`. Its commit
  is later than the published tag and therefore does not alter or invalidate
  the released candidate. Merge it only after its own `governance-fast` passes.
- After that closeout-only PR merges, add closure comments and close every
  task-backed child issue. For #6468 use the closeout-only PR SHA and its
  `governance-fast`; use the published candidate SHA and its `release-full` as
  the separate release evidence.
- Validate every task-backed child issue (#6416–#6429, #6466–#6468, #6471, #6473 and #6475) with
  `python3 scripts/validate-issue-closeout.py --issue-json <issue.json>
  --tasks specs/236-github-full-release-ci/tasks.md --expected-sha
  <candidate-SHA> --require-release-full`; each comment must include the Russian closeout sections,
  task ID, PR number, the exact PR SHA with its successful `governance-fast`
  URL, and the exact candidate SHA with its successful `release-full` URL.
- Before closing the umbrella, validate the whole live inventory with
  `python3 scripts/validate-issue-closeout.py --repo yshishenya/graf --feature
  236 --umbrella 6415 --tasks specs/236-github-full-release-ci/tasks.md
  --expected-sha <candidate-SHA> --require-release-full
  --allow-open-umbrella`; after closing it, run
  the same command without `--allow-open-umbrella`.
- Close umbrella #6415 only through a separate feature-level comment after all
  child issues are reconciled; it is not a task-backed `T000` row.
- The final manifest must show zero orphan or open task-backed child issues.
- Historical `[X]` rows T013-T014 cover the implemented procedure and pre-merge
  reconciliation only. T017 remains `[ ]` through publication and becomes
  `[X]` in the post-release closeout-only PR before #6468 or the umbrella is
  closed; this two-phase order avoids both false completion and a SHA cycle.

Reviewer-owned infrastructure checklist: `checklists/infra.md` records 9/9
requirements accepted, including create-once reservation, exact-SHA binding,
metadata-only evidence and separation of signing/deployment from GitHub CI.
