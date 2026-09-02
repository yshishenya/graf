# Pre-PR validation: Feature 232

Date: 2026-09-02

Lane: `release-deploy` with high-risk macOS startup behavior.

Source baseline: `455990a33f51fe232a8fc3270c8d0a0d27db298b`
(`origin/master`). The implementation is intentionally uncommitted pending the
required owner approval, so this document is development evidence rather than
an exact-SHA release receipt.

## Passed focused checks

- `swift test --filter MeetingTargetRegistryTests`: 19 passed.
- `apps/macos/Installer/Scripts/test-packaged-app-launch.sh`: passed living
  child, immediate-exit, malformed-app, unsupported-architecture and unrelated
  process cases.
- `apps/macos/Installer/Scripts/test-release-signing-custody.sh`: passed,
  including arm64 and x86_64 candidate-startup custody assertions.
- `pytest -q tests/governance/test_dev_runtime.py tests/governance/test_release_candidate.py`:
  17 passed.
- Shell syntax for the changed release scripts and `infra/scripts/ci-local.sh
  --help`: passed.
- Spec Kit analyze: 14 functional requirements and 7 measurable success
  criteria mapped to 22 tasks; zero unresolved critical/high findings.
- Spec Kit converge: zero missing, partial, contradictory or unrequested
  implementation findings.
- Ponytail review: no removable abstraction, dependency or speculative code.

## Production-like candidate checks

- Universal candidate contained both `arm64` and `x86_64` slices.
- Packaged resource layout and Developer ID application signature passed.
- Five arm64 and five x86_64 direct packaged launches remained alive for the
  required five seconds.
- Copied candidates with the packaged baseline removed launched without a
  startup crash on both architectures; the original baseline was restored and
  the candidate signature was revalidated.
- Developer ID installer signature passed for the locally built PKG.

## Repository gate status

The diagnostic dirty-worktree fast run completed its macOS, governance,
CI-contract, build, shell, compose, deployment-evidence, documentation and
whitespace stages. Its receipt is
`.dev/ci-evidence/ci-fast-455990a33f51-6bfcdd23f6fa.json` and is intentionally
`ambiguous`; it is not valid PR or release evidence because the implementation
was not yet committed.

T011 remains open. After owner approval, commit the reviewed diff and run a
clean `infra/scripts/ci-local.sh --fast` on that exact commit before opening the
PR. Full CI, candidate freeze, notarization, stapling, Gatekeeper, manual repair,
Sparkle continuity, public publication and re-download checks remain release
gates after merge.
