# Quickstart: Feature 234

Run from a clean Feature 234 worktree:

```sh
python3 scripts/claim-feature.py --self-test
python3 scripts/check-development-process.py --self-test
python3 scripts/validate-governance-workflow.py .github/workflows/governance-fast.yml
python3 scripts/check_spec_kit_governance.py
pytest -q tests/governance/test_validator_safety.py tests/governance/test_dev_harness.py
actionlint .github/workflows/governance-fast.yml
```

For the closeout rehearsal, inspect each task-backed issue and verify its
checkbox/evidence/comment before using `gh issue close`. The local
`infra/scripts/ci-local.sh` remains a manual diagnostic; the required merge
proof is GitHub `governance-fast` on the exact PR SHA.
