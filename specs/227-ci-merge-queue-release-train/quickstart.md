# Quickstart: Feature 227

## Preflight

```sh
python3 scripts/validate-agent-context.py
python3 scripts/check-development-process.py
python3 scripts/check_spec_kit_governance.py
```

## Local contract checks

```sh
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance/test_ci_evidence_producer.py \
  tests/governance/test_ci_guard.py \
  tests/governance/test_governance_workflow.py \
  tests/governance/test_release_candidate.py
python3 scripts/validate-governance-workflow.py --self-test
```

## Event fixtures

Validate synthetic PR, manual and `merge_group` payloads. A merge-group fixture
must prove synthetic SHA, base SHA and PR mapping. Changed SHA or final tree
drift must produce a terminal non-success receipt.

## PR-ready gate

```sh
infra/scripts/ci-local.sh --fast
```

Record the exact pass evidence path in the PR. Fast coverage remains partial and
is not release approval.

## Release train rehearsal

```sh
infra/scripts/release-candidate.sh train-freeze \
  --source-sha <post-merge-master-sha> --base-sha <base-sha> \
  --synthetic-merge-sha <merge-group-sha> --prs 101,102,103 \
  --features 216,227 --merge-groups mg-1 \
  --pr-receipts pr-101,pr-102,pr-103 --merge-group-receipts mg-1 \
  --operator release-operator \
  --output .dev/release/trains/train-<sha12>.json
infra/scripts/release-candidate.sh train-validate \
  .dev/release/trains/train-<sha12>.json --current

infra/scripts/release-candidate.sh freeze --sha <post-merge-master-sha> \
  --features 216,227 --train .dev/release/trains/train-<sha12>.json \
  --operator release-operator \
  --output .dev/release/candidates/rc-<sha12>.json
infra/scripts/release-candidate.sh validate \
  .dev/release/candidates/rc-<sha12>.json --current
GRAF_CI_CANDIDATE_FILE=.dev/release/candidates/rc-<sha12>.json \
  infra/scripts/ci-local.sh --full
infra/scripts/release-candidate.sh train-attest \
  .dev/release/trains/train-<sha12>.json \
  --candidate .dev/release/candidates/rc-<sha12>.json \
  --evidence .dev/ci-evidence/authoritative-<candidate-id>.json \
  --output .dev/release/trains/train-<sha12>-go.json
infra/scripts/release-candidate.sh decide \
  .dev/release/candidates/rc-<sha12>.json \
  --train .dev/release/trains/train-<sha12>-go.json \
  --evidence .dev/ci-evidence/authoritative-<candidate-id>.json \
  --calver YYYY.MM.DD.N \
  --output .dev/release/decisions/<candidate-id>.decision.json
```

Never reuse evidence after `master` changes. Do not execute production deploy in
this feature.
