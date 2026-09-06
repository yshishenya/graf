# Contract: `macos-diagnostic.yml`

## Input

- `requested_sha`: exactly 40 lowercase hexadecimal characters identifying the
  commit to diagnose. The checked-out SHA must equal this value before
  repository code is executed.

## Required behavior

1. The workflow is manual (`workflow_dispatch`) and uses read-only repository
   permissions.
2. It runs on the same `macos-14` and Swift 6.0.3 baseline as the macOS release
   component.
3. It checks the macOS architecture, build, complete Swift test runner, legacy
   guard and `ContractValidation` on the exact requested SHA.
4. It has no server job, candidate reservation, artifact upload, evidence
   producer, deployment, publication or user-supplied command/filter.
5. Its result is diagnostic only and MUST NOT satisfy `release-full`,
   `train-attest`, `decide`, deployment or issue closeout release evidence.

## Release boundary

A successful diagnostic run only permits preparation of a new frozen candidate.
That candidate still requires one successful complete `release-full` with both
server and macOS component results and one aggregate authoritative record.
