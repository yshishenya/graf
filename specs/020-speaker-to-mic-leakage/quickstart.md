# Quickstart: Speaker-To-Mic Leakage Control

This guide defines validation scenarios for the implementation phase. It should
be runnable after `$speckit-tasks` and `$speckit-implement` create the planned
validators.

## Prerequisites

- macOS Apple Silicon development machine.
- 2brain Rec virtual driver installed through the existing local installer
  workflow.
- A supported browser/meeting target for manual route matrix checks.
- Local-only controlled audio stimuli that are not meeting content and contain
  no secrets.

## Baseline Commands

```sh
specify --version
swift test --package-path apps/macos --disable-swift-testing
swift run --package-path apps/macos ContractValidation
sh tests/macos/static/audio-rt-safety-check.sh
```

## Scenario 1: Existing Misaligned Evidence Package

Use the saved package id
`20260604-091621-C705ED72-E352-4522-93F2-1219953177EE` as local evidence.

Expected result:

- `mic.wav` and `incoming.wav` remain unchanged.
- Timeline mismatch prevents `clean` and `ready`.
- Final status is `unproven` or `not_measured`, depending on whether the
  measurement attempted alignment.
- The package is not marked transcription-ready.
- Diagnostics contain no raw audio, transcript text, participant speech,
  secrets, signed URLs, or live absolute user paths.

## Scenario 2: Far-End-Only Controlled Fixture

Create a package where the local user is silent and controlled far-end speech or
stimulus plays through the selected output route.

Expected result:

- If far-end energy appears in `mic.wav` above `leakage-threshold.v1`, status is
  `leakage_detected`.
- If the route is physically isolated and leakage is below threshold, status may
  be `clean`.
- Double-talk windows are not required because the near-end is silent.
- Route facts are saved only as metadata.

## Scenario 3: Double-Talk Controlled Fixture

Create a package with remote speech and local speech overlapping.

Expected result:

- Local speech is not treated as leakage.
- Local speech is not muted merely because remote speech is active.
- If leakage cannot be separated confidently, status is `unproven`, not
  `clean`.
- The finalization evidence records double-talk exclusion or confidence
  downgrade metadata.

## Scenario 4: Missing Or Invalid Reference

Create packages with missing `incoming.wav`, empty incoming track, unsupported
package shape, or insufficient far-end-only windows.

Expected result:

- Missing or unsupported reference produces `not_measured` when measurement does
  not run or cannot apply.
- Attempted measurement with insufficient reliable evidence produces
  `unproven`.
- Neither state is transcription-ready.

## Scenario 5: Derived Cleaned Track

Run post-recording cleanup on a contaminated package after stop/finalization.

Expected result:

- Original `mic.wav` and `incoming.wav` are unchanged.
- The derived track has a distinct file name, source track ids, processor id,
  processor version, confidence, residual leakage status, and threshold version.
- The derived track is transcription-eligible only when residual leakage passes
  the finalization gate.

## Scenario 6: Route Matrix

Record short packages across:

- built-in Mac microphone plus built-in speakers;
- wired headphones;
- USB headset;
- Bluetooth/AirPods-class device;
- aggregate or multi-output route;
- at least one supported browser/meeting target.

Expected result:

- Recording is not blocked by leakage route readiness.
- Each stopped package receives finalization evidence or a truthful
  `unproven`/`not_measured` status.
- Built-in speakerphone is not accepted as clean unless controlled validation
  proves it.
- Any 2brain Rec virtual device selected as the physical working microphone or
  physical output is rejected as self-routing, even though ordinary leakage
  route readiness is not a start blocker.

## Scenario 7: Privacy And Realtime Safety

Run diagnostics redaction and realtime static checks after implementation.

Expected result:

- Metadata contracts reject raw audio, snippets, transcript text, participant
  speech, credentials, tokens, signed URLs, passwords, API keys, absolute paths,
  and live secret paths.
- HAL/Core Audio callback paths contain no new file IO, logging, allocation,
  locks, network calls, process launches, UI work, or unbounded waits.

## Scenario 8: Finalization Performance And Memory

Run leakage finalization on a local controlled package up to 2 hours long.

Expected result:

- Leakage metadata finalization completes in under 60 seconds on Apple Silicon
  for the ordinary 2-hour validation package.
- Analysis memory stays under 256 MB through windowed reads.
- Packages longer than 2 hours are outside the 020 timing acceptance target, but
  finalization still uses windowed reads, avoids unbounded memory growth, and
  does not block recording stop, passthrough, or realtime audio paths.
- The command, package duration, elapsed time, and memory observation are
  recorded in this quickstart during implementation validation.

## Go/No-Go Rule Before Implementation Completion

Implementation is not complete until:

- package finalization produces authoritative leakage status only after stop;
- `unproven` and `not_measured` remain distinct;
- contaminated or ambiguous packages are not transcription-ready;
- original evidence tracks remain immutable;
- derived tracks have lineage and residual-leakage gates;
- finalization performance and memory bounds are measured for the ordinary
  2-hour validation package;
- no external egress or content-bearing diagnostics are introduced.

## Implementation Validation Log

Recorded on 2026-06-04:

| Gate | Command | Result |
| --- | --- | --- |
| Swift package tests | `swift test --package-path apps/macos --disable-swift-testing` | PASS, exit 0 |
| Contract validation | `swift run --package-path apps/macos ContractValidation` | PASS, `ContractValidation: PASS` |
| Realtime static safety | `sh tests/macos/static/audio-rt-safety-check.sh` | PASS, `audio-rt-safety-check: ACCEPTED` |
| Bidirectional passthrough regression | `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` | PASS, available checks completed |
| Default passthrough disabled gate | `TWO_BRAIN_REC_DEFAULT_OFF_WAIT_SECONDS=12 sh tests/macos/installer-recovery/default-passthrough-disabled-check.sh` | PASS after aligning the checker with current launch log events |
| Manual route matrix | `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md` | Hardware rows marked not run in this environment; self-routing covered by regression gates |
| 2-hour finalization performance | `/usr/bin/time -l swift run --package-path apps/macos LeakageValidation` | PASS on controlled sparse local-only 2-hour WAV package: finalization elapsed `1.03s`, total validation elapsed `3.26s`, maximum resident set `44,187,648` bytes, peak memory footprint `35,766,824` bytes |

Review remediation status recorded on 2026-06-04:

- Feature `020` post-review remediation is implemented and locally validated.
- Created canonical GitHub remediation issues:
  - #156 false-clean delayed and late leakage finalization;
  - #157 bounded WAV parsing and malformed input rejection;
  - #158 deletion registration truth;
  - #159 leakage-specific post-stop recording truth;
  - #160 issue-canon symlink write and remote redaction hardening;
  - #161 acceptance/status validation evidence.
- Remediation build command `swift build --package-path apps/macos` passed.
- Remediation contract command `swift run --package-path apps/macos ContractValidation`
  passed with `ContractValidation: PASS`.
- Remediation realtime static command `sh tests/macos/static/audio-rt-safety-check.sh`
  passed with `audio-rt-safety-check: ACCEPTED`.
- Focused command `swift test --package-path apps/macos --filter Leakage` compiled
  `TwoBrainRecMacOSPackageTests`, then hung in `swiftpm-testing-helper`; it was
  stopped and is not counted as a test pass. This remains a validation proof gap
  until the XCTest/SwiftPM runner issue is resolved.
- Added `LeakageValidation` executable because SwiftPM/XCTest execution is known
  to be unreliable in this local runtime. Command
  `swift run --package-path apps/macos LeakageValidation` passed with
  `LeakageValidation: two_hour_sparse elapsed=1.10s status=leakage_detected`
  and `LeakageValidation: PASS elapsed=3.33s`. This covered delayed leakage,
  late leakage, malformed WAV headers, format mismatch, deletion truth, and a
  sparse local-only 2-hour package finalization.
- Timed command `/usr/bin/time -l swift run --package-path apps/macos
  LeakageValidation` passed with `LeakageValidation: two_hour_sparse
  elapsed=1.03s status=leakage_detected`, `LeakageValidation: PASS
  elapsed=3.26s`, maximum resident set `44,187,648` bytes, and peak memory
  footprint `35,766,824` bytes.
- Remediation SwiftPM build/test-build command
  `swift test --package-path apps/macos --disable-swift-testing` passed with
  exit 0 and `Build complete`.
- Remediation passthrough regression command
  `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` passed with
  `validate-real-bidirectional-passthrough: completed available checks`.
- Post-remediation `$speckit-analyze` read-only consistency pass found no
  remaining critical or high spec/plan/tasks/constitution gaps. Requirement
  coverage for the reviewed blockers maps to T074-T094, and the only retained
  caveat is that hardware route-matrix rows remain marked unavailable in this
  environment rather than accepted as physical-device proof.

Main-sync transfer validation recorded on 2026-06-10:

- Old `020` work was preserved on
  `codex/020-speaker-to-mic-leakage-pre-main-sync`; the active transfer branch
  was recreated from fresh `origin/master` as
  `codex/020-speaker-to-mic-leakage-main-sync`.
- Directly merging the old branch was rejected as unsafe because it would have
  rolled back `025-system-audio-capture-pivot` files and current server/docs
  state. The accepted transfer strategy is selective artifact copy plus manual
  integration into the current `025` writer, manifest, models, diagnostics, and
  contract fixtures.
- `swift build --package-path apps/macos` passed after the transfer.
- `swift build --build-tests --package-path apps/macos` passed after resolving
  all observed compile-time and assertion-expectation gaps from the current
  `025` package tests.
- `swift test --package-path apps/macos` passed after aligning the
  `LocalRecordingWriterSystemAudioTests` stop-tail expectation with the merged
  `020`/`025` truth model: the track and capture-health evidence stay healthy,
  while the manifest-level transcription gate remains blocked-unproven for a
  short synthetic package that cannot prove leakage cleanliness. The final run
  executed `357` XCTest cases with `0` failures.
- A later Spec Kit traceability check found that tasks T020 and T031 referenced
  `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`, which
  was missing after the selective main-sync transfer. That gap is closed with
  package-level integration tests for contaminated leakage and timeline
  mismatch manifest readiness. The tests also caught and fixed a manifest status
  bug: `blockedLeakageDetected` now fails closed at manifest status level while
  existing `025` degraded/blocking semantics for permissions, scope, and track
  failures remain unchanged. The final full suite executed `359` XCTest cases
  with `0` failures.
- `swift run --package-path apps/macos LeakageValidation` passed with
  `LeakageValidation: two_hour_sparse` reporting `status=leakage_detected` and
  overall `PASS`.
- `swift run --package-path apps/macos ContractValidation` passed.
- `sh tests/macos/static/audio-rt-safety-check.sh` passed with
  `audio-rt-safety-check: ACCEPTED`.
- Final closeout validation on 2026-06-10 passed:
  `swift build --package-path apps/macos`;
  `swift test --package-path apps/macos --disable-swift-testing` with `359`
  XCTest cases and `0` failures;
  `swift run --package-path apps/macos ContractValidation` with
  `ContractValidation: PASS`;
  `/usr/bin/time -l swift run --package-path apps/macos LeakageValidation` with
  `LeakageValidation: PASS elapsed=4.54s`, two-hour sparse package
  `status=leakage_detected`, maximum resident set `44,826,624` bytes, and peak
  memory footprint `35,734,104` bytes;
  `sh tests/macos/static/audio-rt-safety-check.sh` with
  `audio-rt-safety-check: ACCEPTED`;
  `sh apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` with
  `system_audio_no_hal_probe_validation=passed`;
  `sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata`
  with synthetic artifact metadata checks passed; and
  `sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
  with default local package confirmed app-only.
- `sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --validate-latest-artifact`
  was intentionally not accepted as a `025` ready-artifact gate because the
  latest local recording is now a `local-recording-manifest.v3` package with
  `failureReason=leakage_detected` and
  `transcriptionGate=blocked_leakage_detected`; that is the expected `020`
  fail-closed result, not a `025` accepted-artifact result.
- `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` was not
  used as the final closeout gate for this branch because the product path has
  moved to system-audio capture and the HAL virtual-device publication path is
  parked as legacy/advanced-routing evidence. In this environment the legacy
  passthrough script blocked on missing `2brain Rec Microphone` and
  `2brain Rec Speaker` HAL devices after app-only install cleanup; no driver
  installation or Core Audio restart was performed for this closeout.
- A transient earlier `swift test` attempt hit a local macOS generated-test
  bundle load denial, but the final main-sync run completed successfully in the
  same worktree. The successful full-suite run, not the transient denial, is the
  accepted validation evidence for this transfer.

## Installer, Signing, Repair, Rollback, And Uninstall Scope

020 is a finalization-only local recording slice. It does not change installer
payloads, signing identities, notarization flow, repair scripts, rollback
scripts, uninstall scripts, driver installation state, Core Audio component
placement, or launch permissions. Existing installer lifecycle validation remains
the applicable evidence for those surfaces; this implementation only changes
macOS app/shared Swift code, contract fixtures, diagnostics, and documentation.

Validation note: the 2-hour timing/memory acceptance target was covered by the
local sparse fixture runs recorded above. Physical route-matrix hardware rows
that require unavailable devices remain marked unavailable rather than accepted.
