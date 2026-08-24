# Implementation Plan: Политики автозаписи по приложениям

**Branch**: `codex/199-per-app-recording-policies` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

## Summary

Replace the binary target allowlist with a target-scoped three-state rule while
retaining the existing detector, workspace policy and capture gates. Update the
prompt so its 8-second timeout starts only the current recording and never saves
the checkbox choice. Update native settings to use compact theme-style radio
cards per target and one equivalent bulk selector; keep technical switches but
move their long copy to hints.

## Technical Context

**Language/Version**: Swift 5.9+, SwiftUI, AppKit, existing macOS package

**Primary Dependencies**: Foundation, SwiftUI, AppKit, existing registry and
capture services; no new dependency

**Storage**: Existing atomic JSON settings file with backward-compatible Codable
migration; no server schema or database change

**Testing**: Swift XCTest focused policy/countdown/settings suites plus synthetic
desktop accessibility smoke

**Risk / Validation Lane**: high-risk-feature — recording start behavior, privacy,
prompt consent, settings policy and accessibility

**Release Gate**: no deploy or release; full repository CI is a separately
reported lane and is not claimed unless explicitly run

**Target Platform**: macOS native app

## Constitution Check

### Before research

- **PASS — Capture-first**: reuse the existing native system-audio-first path and
  do not add routing or a new capture engine.
- **PASS — Visible consent and control**: the prompt, 8-second countdown, explicit
  Start/Skip, target allowlist, visible indicator and one-action Stop remain.
- **PASS — Target boundary**: rules are exact target IDs; workspace policy remains
  separate and fail-closed.
- **PASS — Privacy**: timeout does not create durable permission; ambiguous legacy
  state becomes `ask`; diagnostics remain metadata-only.

### After design

- **PASS — Minimal model**: one enum map and one mixed-state presentation value;
  no new service, endpoint, table or dependency.
- **PASS — Lifecycle**: prompt outcomes distinguish current meeting action from
  persisted target policy; duplicate terminal actions remain idempotent.
- **PASS — Accessibility**: theme-style radio cards have keyboard/VoiceOver
  labels, hints are discoverable without permanent technical paragraphs, and
  countdown state is announced truthfully.
- **PASS — Migration**: old binary/global fields cannot grant cross-target
  automatic recording.

## Implementation Phases

1. **Model and migration** — add `AutomaticRecordingRule`, Codable map, helper
   resolution and legacy migration tests.
2. **Policy and detector** — resolve `always/ask/never`, keep workspace policy and
   final gates, and pass the rule map through detector snapshots.
3. **Prompt semantics** — preserve the 8-second timeout as current-start only;
   persist rules only from explicit button+checkbox actions; remove timeout
   suppression path and technical prompt copy.
4. **Settings UI** — replace binary checkboxes/bulk buttons with theme-style radio
   cards, mixed bulk state, short technical switches and info hints; remove bundle
   IDs and long inline descriptions.
5. **Validation and docs** — run focused Swift tests, synthetic UI/accessibility
   smoke, source-contract assertions and update changelog/status.

## Project Structure

```text
specs/199-per-app-recording-policies/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/automatic-recording-policy.md
├── quickstart.md
└── checklists/{requirements,capture-safety,security,ux}.md

apps/macos/Shared/Sources/MeetingDetection/
├── MeetingDetectionPolicy.swift
└── MeetingDetectionModels.swift

apps/macos/RecApp/Sources/MeetingDetection/
├── MeetingDetectionSettingsStore.swift
├── MeetingDetectionSettingsView.swift
└── MacOSMeetingActivityDetector.swift

apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift
apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift
apps/macos/Shared/Tests/CaptureControlV5Tests.swift
```

## Validation Plan

- Run `swift test --package-path apps/macos --disable-swift-testing --filter
  'MeetingDetectionPolicyTests|MeetingDetectionCountdownTests|CaptureControlV5Tests'`.
- Run the synthetic settings/prompt scenarios from `quickstart.md`.
- Run the focused macOS accessibility/source-contract tests that cover prompt and
  capture indicator behavior.
- Run `infra/scripts/ci-local.sh --fast` only if the user explicitly requests the
  broader repository gate; do not claim full CI otherwise.
- Never run production deploy, Sparkle publication or replace the installed app
  in this feature.

## Complexity Tracking

No constitution violations. The only new persisted concept is the target-scoped
three-state rule required to distinguish unset, always and never.
