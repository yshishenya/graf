# Contract: Legacy Driver Retirement Boundary

## Forbidden active surface

Active source, package, installer, test, QA, and current documentation MUST NOT
contain an executable or configurable path for:

- `apps/macos/AudioDriver` or an equivalent HAL plug-in target;
- `CShmHelpers`, `SharedAudioMemory`, or the old bridge name;
- `PassthroughBridge`, `PassthroughRouteEngine`, or automatic coordinator;
- GRAF/2brain virtual microphone or speaker publication;
- driver install/package/update/repair/rollback choice or payload;
- app launch flags that start or arm passthrough;
- driver readiness/health/setup UI or recording blockers;
- driver-only runtime probes, fixtures, QA gates, or synthetic checks.

Renaming or disabling one of these paths does not satisfy removal.

## Permitted references

References are permitted only in:

- historical `specs/` and explicitly historical failure/evidence records;
- the superseding ADR and current retirement documentation;
- the architecture guard's own forbidden-pattern declaration;
- bounded manual guidance for inspecting/removing an already installed proof
  component.

The allowlist MUST be explicit and narrow. Generated `.build` output is ignored
and must be cleaned before package-content inspection.

## Guard behavior

The retirement validator MUST:

- be read-only;
- scan reviewed active roots rather than the entire repository blindly;
- distinguish generic Core Audio/device terminology from exact retired symbols;
- fail with the file and matched pattern;
- perform no install, uninstall, file deletion, evidence write, or service
  restart.

## Future architecture

Future advanced routing requires a new Spec Kit feature, threat/capture review,
and independent safety proof. It may not restore this implementation by
re-enabling a toggle or reverting the absence guard.
