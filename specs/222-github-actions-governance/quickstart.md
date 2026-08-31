# Quickstart: Feature 222

All checks are metadata-only. Do not add secrets, raw logs, audio, transcripts
or private meeting data to evidence.

## 1. Feature pointer and governance

```sh
cat .specify/feature.json
python3 scripts/claim-feature.py --self-test
python3 scripts/check_spec_kit_governance.py
python3 scripts/validate-changelog-fragments.py
```

Expected: Feature `222`, branch `codex/222-github-actions-governance`, no
unresolved clarification markers, and no legacy exception.

## 2. Workflow contract

```sh
python3 scripts/validate-governance-workflow.py
pytest -q tests/governance/test_governance_workflow.py
```

Expected: canonical job/check name, PR target, SHA guard, cancellation and
forbidden-command checks pass.

## 3. Local fast lane

```sh
GRAF_CI_REQUESTED_SHA="$(git rev-parse HEAD)" infra/scripts/ci-local.sh --fast
```

Record the exact evidence path. A changed SHA makes this result stale.

## 4. GitHub operator proof

After the PR is opened, observe one successful `governance-fast` check and one
synthetic superseding commit where the older run is cancelled. Only then enable
Actions and the required `governance-fast` check on `master`.

## 5. Release boundary

Do not run Full CI, CD, migration, or product release commands for this feature.
Those belong to the frozen release-candidate process in
`docs/agent-guidance/release-and-validation.md`.
