# Pre-PR validation: Feature 232

Date: 2026-09-02

Lane: `release-deploy` with high-risk macOS startup behavior.

Validated implementation commit:
`8d6ac5af3674f0a89f9662b68e1e499eff0736ba`. This is PR evidence, not an
exact-SHA release receipt; the authoritative Full CI remains deferred to the
later combined frozen release candidate.

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

Clean `infra/scripts/ci-local.sh --fast` passed on the validated implementation
commit in 108 seconds:

- governance: 169 passed;
- macOS Swift: 783 passed;
- CI contracts: 60 passed;
- build, contract validation, shell, compose, deployment-evidence,
  documentation, whitespace and final cleanliness: passed;
- coverage: `partial`; next gate: `full_before_release`;
- receipt: `.dev/ci-evidence/ci-fast-8d6ac5af3674-02333d4c3aaf.json`.

Full CI, candidate freeze, notarization, stapling, Gatekeeper, manual repair,
Sparkle continuity, public publication and re-download checks remain deferred
to the later combined release and are not part of this PR publication step.
