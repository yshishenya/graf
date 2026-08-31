# Workflow Contract

## Canonical identity

- file: `.github/workflows/governance-fast.yml`
- job id: `governance-fast`
- check name: `governance-fast`
- artifact: `graf-governance-fast-evidence`

## Required invariants

- trigger: `pull_request` targeting `master`; `workflow_dispatch` is explicit;
- `concurrency.cancel-in-progress` is exactly `true`;
- checkout uses PR head SHA, not a moving branch;
- requested/checkout/observed SHA mismatch exits non-zero;
- only `infra/scripts/ci-local.sh --fast` and metadata validators run;
- artifact is uploaded only after validator success;
- no production, migration mutation, volume deletion or secret export command;
- cancellation and stale evidence cannot be merge-ready.
