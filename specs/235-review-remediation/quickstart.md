# Quickstart

```sh
python3 scripts/claim-feature.py --self-test
python3 scripts/validate-issue-closeout.py --self-test
python3 scripts/validate-pr-metadata.py --self-test
pytest -q tests/governance/test_validator_safety.py tests/governance/test_governance_workflow.py
python3 scripts/validate-governance-workflow.py
git diff --check
infra/scripts/ci-local.sh --fast
```

All evidence must refer to one clean exact source SHA. Do not run production
deploy or alter root `CHANGELOG.md` in this feature.
