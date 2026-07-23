# Implementation Plan: Восстановление автозаписи встреч

**Branch**: `124-restore-automatic-recording` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/124-restore-automatic-recording/spec.md`

## Summary

Feature 124 restores the target-scoped automatic meeting-recording workflow
that Feature 121 temporarily removed: the verified native-app settings list,
per-target permissions, the prompt opt-in checkbox, the eight-second visible
countdown and automatic start. The implementation reuses the existing settings
fields, registry, policy gates, native capture path and floating prompt. The
diff is intentionally limited to restoring the deleted branches and replacing
tests/docs that currently assert their absence.

## Technical Context

**Language/Version**: Swift 6 on macOS; Markdown/YAML/JSON for product and
Spec Kit documentation

**Primary Dependencies**: SwiftUI/AppKit, existing
`MeetingTargetRegistryStore`, `MeetingDetectionPolicy`,
`RecordingPrerequisiteGate`, `CaptureSessionController`, and current native
ScreenCaptureKit/AVFoundation capture services. No new dependency.

**Storage**: Existing JSON `MeetingDetectionSettingsStore` and cached canonical
meeting-target registry. Existing target-scoped fields are preserved; no schema
or migration reset is introduced.

**Testing**: Swift Package XCTest/static source-contract tests in
`apps/macos/Shared/Tests/`, focused macOS package tests, ContractValidation,
and the Feature 124 quickstart scenarios.

**Risk / Validation Lane**: High-risk feature — restores capture start behavior,
privacy-sensitive target policy, native settings UX, timer-driven start and
visible consent surfaces. Full Spec Kit sequence, focused XCTest, quickstart,
Ponytail review and repository CI are required.

**Release Gate**: No deploy in this worktree. A later rollout requires explicit
approval, signed/notarized macOS app proof, `cd-remote.sh --dry-run`, local CI,
and the product/release gates from `docs/agent-guidance/release-and-validation.md`.

**Target Platform**: macOS 14+ Apple Silicon native desktop app; current
registry may contain browser/future targets but only verified macOS native
targets appear in the auto-record list.

**Project Type**: Native macOS desktop capture app with a local SwiftUI/AppKit
settings and floating-prompt surface.

**Performance Goals**:

- Prompt countdown updates at the existing SwiftUI timeline cadence without
  blocking the capture path.
- Manual Start remains immediate and the eight-second timer starts only after
  the prompt is presented.
- Automatic target start is emitted at most once per stable detector episode.
- A prompt or automatic-start trigger is handled at most once while the
  current prompt/session decision is active.
- Settings changes persist atomically and are visible after the existing
  settings-change notification.

**Constraints**:

- Do not revive the removed separate audio-routing implementation.
- Do not weaken `RecordingPrerequisiteGate`, permission checks, visible state,
  one-action Stop, suppression, or workspace policy.
- Do not start from arbitrary system audio, browser bundles, media playback,
  unknown apps, diagnostic-only targets or a second active session.
- Reuse the existing old code path from the Feature 121 parent where it matches
  current types; preserve unrelated post-121 fixes in the working tree.
- Maintain metadata-only logs/evidence and do not add transcript/audio content.
- Keep the exact labels and eight-second countdown as contract-tested behavior.

**Scale/Scope**: One active local capture per device; all verified native targets
in the current registry; one settings screen and one floating prompt. No new
registry discovery, server API, audio engine or cross-platform behavior.

## Constitution Check

*GATE: PASS before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Result | Evidence / Design Response |
|---|---|---|
| Capture-First MVP Integrity | PASS | Reuses the current macOS system-audio-first + explicit microphone path and `CaptureSessionController`; no legacy routing or second writer is restored. |
| Visible Consent And User Control | PASS | Auto-record is exact-target and policy-gated; the prompt has a visible eight-second countdown, opt-in checkbox and dismissal; automatic and manual capture retain the local indicator and one-action Stop. |
| Plaintext Observability For Internal MVP | PASS | No meeting-content logging, new external egress, or observability storage is added. |
| Deletion Truth And Lifecycle Accounting | PASS | No meeting artifact lifecycle or deletion behavior changes. |
| Spec-Driven Delivery With Testable Gates | PASS | Feature 124 has spec, clarify outcome, plan, research, data model, UI contract, quickstart, checklists, tasks and analyze before implementation. |

**Gate conclusion**: PASS before Phase 0 research. The restoration is an
explicitly approved product correction and does not bypass the safety rules
that motivated Feature 121's temporary simplification.

## Validation Plan

Focused checks:

- `swift test --package-path apps/macos --disable-swift-testing --filter MeetingDetectionPolicyTests`
- `swift test --package-path apps/macos --disable-swift-testing --filter CaptureControlTests`
- `swift test --package-path apps/macos --disable-swift-testing --filter AppControlAccessibilityTests`
- `swift run --package-path apps/macos ContractValidation`
- Feature 124 quickstart scenarios for settings, prompt timer cancellation,
  auto-record policy, blocked gates, duplicate events and documentation search.
- `infra/scripts/ci-local.sh` at closeout because shared capture code, UX and
  tests change. No deployment command is run in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/124-restore-automatic-recording/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── issues.md
├── contracts/
│   └── recording-workflow.md
├── checklists/
│   ├── requirements.md
│   ├── capture-privacy.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift
├── RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift
├── RecApp/Sources/MeetingDetection/MeetingDetectionSettingsStore.swift
├── Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift
└── Shared/Tests/
    ├── CaptureControlV5Tests.swift
    ├── AppControlAccessibilityTests.swift
    └── MeetingDetectionPolicyTests.swift

docs/
├── current-product-status.md
├── prd-voice-layer-final.md
└── agent-guidance/product-gates.md
```

**Structure Decision**: Keep the existing native meeting-detection module and
its Swift Package tests. The UI, policy and detector are restored in place; the
settings store/registry remain the existing persistence and source-of-truth
boundary. Feature 124 docs are the new durable owner of the restored contract.

## Phase 0 Research Summary

Phase 0 findings are recorded in [research.md](./research.md). The key decision
is to restore the exact target-scoped branches from the Feature 121 parent and
the earlier prompt implementation, while retaining later safety and logging
fixes present at the current base.

## Phase 1 Design Summary

- [data-model.md](./data-model.md) maps the existing settings, registry,
  prompt, policy action and capture-session entities.
- [contracts/recording-workflow.md](./contracts/recording-workflow.md) defines
  the user-visible and policy boundaries that must remain stable.
- [quickstart.md](./quickstart.md) gives focused and repository validation
  scenarios without recording real meeting content.

## Complexity Tracking

No constitution violation is introduced. A new service, dependency, registry or
capture abstraction is intentionally rejected because the requested behavior
already exists in the repository history and the current model still retains
its persisted fields.

## Constitution Re-check After Phase 1 Design

| Gate | Result | Evidence |
|---|---|---|
| Automatic recording remains policy-gated | PASS | `autoRecord` is emitted only for exact target opt-in after existing prerequisites. |
| Timer cannot bypass capture truth | PASS | Countdown resolves through the same start callback and remains disabled when prerequisites are unavailable. |
| Cancelled or competing prompt work cannot start capture | PASS | Cancelled timer tasks return before `resolveStart()` and output handling coalesces one recording trigger while a prompt/session decision is active. |
| Active capture remains visible and stoppable | PASS | Existing native session, status item and matching-target end/Stop path are reused. |
| Unknown/non-target signals remain blocked | PASS | Existing registry/filter suppression and no new discovery path remain authoritative. |
| No legacy routing resurrection | PASS | Plan and tasks touch only existing detection/prompt/settings surfaces. |
| Validation and documentation are durable | PASS | Focused tests, quickstart, product gates, constitution, status and historical supersession notes are required. |
