# Feature 194 — implementation evidence

Date: 2026-08-23
Branch: `194-global-auto-start-defaults`
Code baseline: `661130ac159864d6e15c00b2170e736441dd9f40` (equals
`origin/master` at validation time)

## Scope and safety boundary

- Validation lane: `high-risk-feature` (capture start/stop, policy, permissions,
  prompt UX and multi-workspace authorization).
- The implementation keeps the system-audio-first capture path, verified native
  target allowlist, visible indicator and one-action Stop.
- Fresh-install defaults never create an acknowledgement. Without the exact
  current acknowledgement, the prompt is visible, `Записать сейчас` is an
  explicit current action, and timeout/saved-target automatic starts are blocked.
- Global policy remains internal-only and approval-gated in this implementation.
  Release and deployment actions are separate release-gates and are recorded
  outside this implementation evidence.

## End-to-end checks

| Path | Result | Evidence |
|---|---|---|
| Server config: disabled/scoped/global/invalid approval/ambiguous workspace/dates | PASS | `PYTHONPATH=src uv run --extra dev pytest tests/unit/test_config_validation.py ...` — 71 passed in the focused unit file; the global cases are included in this count. |
| Registry API: scoped compatibility, global scope, opaque refs, ETag and fail-closed expiry | PASS | `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_meeting_detection_api_contract.py -q` — 6 passed; isolated disposable PostgreSQL was removed by the harness. |
| Clean settings file | PASS | `MeetingDetectionPolicyTests.testFreshInstallDefaultsApplyOnlyOnceAndNeverOverwriteAnExplicitFile`; detection becomes `detect_and_ask`, verified native target IDs are selected, marker is persisted, and a second application returns no update. |
| Legacy settings file | PASS | `MeetingDetectionPolicyTests.testExistingSettingsWithoutDefaultsMarkerRemainUserControlled` and `testLegacySettingsKeepTargetSelectionButRequireNewAcknowledgement`; missing marker decodes as user-controlled. |
| Target filtering and cached policy decoding | PASS | `MeetingTargetRegistryTests` — 15 passed; browser, diagnostic, missing-bundle and unverified targets remain excluded, while a missing `scope` decodes as `workspace`. |
| Prompt/no-ack path | PASS | `MeetingDetectionPolicyTests` — 34 passed; selected targets emit `.prompt` when authorization is false, explicit button remains available, and saved-target auto-record needs authorization. |
| Capture and UX source contracts | PASS | `CaptureControlTests` — 43 passed; prompt copy, accessibility state, timeout branch and final policy/ack recheck are asserted. |
| Full shared Swift behavior | PASS | `swift test --filter TwoBrainRecSharedTests` — 752 passed, 0 failures. |
| Swift contract executable | PASS | `swift run --package-path apps/macos ContractValidation` — `ContractValidation: PASS`. |
| Python lint | PASS | `PYTHONPATH=src uv run --extra dev ruff check .` — all checks passed. |
| Compose rendering | PASS | `docker compose -f infra/docker-compose.yml config --quiet`. |
| Repository fast lane | PASS | `infra/scripts/ci-local.sh --fast` — legacy-audio guard, `1173 passed`, lint and Python compile passed. |
| Evidence safety scan | PASS | `scan_deployment_evidence_text` accepted this metadata-only evidence file; no forbidden content was found. |
| Dev app packaging smoke | PASS | `GRAF_DEV_ORIGIN=http://127.0.0.1:8081 sh apps/macos/Scripts/build-dev-app.sh`; a separate signed `GRAF Dev.app` was built and verified, without installing over the public app. |
| Master synchronization | PASS | `HEAD`, `origin/master` and merge-base all equal `661130ac159864d6e15c00b2170e736441dd9f40`. |

## Logic audit matrix

1. **Registry unavailable** — no defaults and no prompt; detector waits for a
   valid remote/cache registry.
2. **First valid registry, missing settings file** — detection and all verified
   native targets are persisted once; acknowledgement remains absent.
3. **Existing or legacy settings** — target selection and detection mode are
   preserved; registry refresh cannot overwrite them.
4. **Verified target, no acknowledgement** — visible prompt; button can start
   the current recording after the normal capture prerequisites; timeout and
   saved-target paths fail closed.
5. **Explicit “Всегда писать это приложение”** — target selection and the exact
   user/workspace/device-bound acknowledgement are saved atomically; a failed
   save restores the in-memory settings snapshot.
6. **Acknowledgement/policy changed or expired** — automatic paths recheck the
   current policy, acknowledgement, target, permissions, storage, active
   session, indicator and Stop path immediately before capture.
7. **Global policy** — every authenticated workspace gets the same global
   `policyRef`; subject/device references differ and remain opaque. Scoped mode
   still requires the exact configured workspace.
8. **Unsupported target** — browser/manual-only, diagnostic, unknown, media and
   arbitrary-audio signals cannot become default targets or automatic starts.

## Spec Kit consistency check

- All FR-001…FR-015 and SC-001…SC-007 have at least one task mapping.
- All tasks T001…T017 have implementation or validation evidence.
- The plan, checklists and implementation agree on the no-ack prompt boundary:
  no hidden automatic start before explicit user acknowledgement, while the
  acknowledged timeout/saved-target flow retains Feature 193 gates.
- No constitution blocker remains: visible consent, manual controls, native
  capture, target allowlist, opaque references and metadata-only diagnostics are
  preserved. External/customer notice and production rollout remain out of
  scope.

## Implementation-evidence boundary

- This file records the implementation validation lane before release
  packaging. Full CI, production CD, notarized packaging and Sparkle
  publication are release gates and must be evidenced by the release/deployment
  receipt for the exact merged SHA.
