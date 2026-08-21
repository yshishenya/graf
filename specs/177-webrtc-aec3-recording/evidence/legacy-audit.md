# Legacy capture audit

Date: 2026-08-21

## Scope and result

- `AECProductSurfaceTests`: 4 passed, 0 failed.
- `validate-no-legacy-audio-driver.sh`: covered again by the repository gate.
- Active v5 writer/timeline/app surfaces create exactly one mandatory
  `RecordingEchoProcessor` and one canonical mix.
- No selectable Apple voice-processing, Feature 038/039 experiment, Feature
  106 alternate writer, retired audio driver, raw-microphone fallback or second
  ASR artifact is reachable from the active recording path.
- Historical Feature 038/039/106 specs, evidence and compatibility readers were
  retained as records; they are not runtime selectors.
- The obsolete non-PTS `LocalRecordingSampleSource` FIFO, duplicate flat audio
  buffer, runtime casts and unused ContractValidation sources were removed. The
  live writer now accepts only one bounded PTS-bearing source protocol.
- Generic uses of the word `fallback` outside capture remain unrelated product
  behavior and were not removed.
- Active product and QA copy now describes mandatory AEC3; historical release
  receipts were not rewritten.

The audit is source- and contract-based. It does not claim installed-app
speakerphone quality.
