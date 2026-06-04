# Test Results

Date: 2026-06-04

## Swift Package Tests

Command:

```sh
cd apps/macos
swift test
```

Result: passed.

Notes:

- The package built successfully.
- The full XCTest runner returned exit code 0.
- New `019` coverage includes route evidence contracts, autorepair, client activity, route release decisions, recording timeline evidence, validation aggregation, diagnostics redaction, and acceptance matrix behavior.

## Foundation Validation Scripts

Command:

```sh
apps/macos/Scripts/validate-live-route-readiness.sh
```

Result: passed.

Summary lines:

- `live-mic-readiness-check: ACCEPTED`
- `live-speaker-readiness-check: ACCEPTED`
- `live-self-routing-check: ACCEPTED`
- `live-latency-check: ACCEPTED`
- `live-leakage-check: ACCEPTED`
- `live-route-outage-check: ACCEPTED`
- `validate-live-route-readiness: completed available checks`

Command:

```sh
apps/macos/Scripts/validate-recording-artifact-format.sh
```

Result: passed.

Summary lines:

- `ContractValidation: PASS`
- `audio-rt-safety-check: ACCEPTED`
- `recording_artifact_format_validation=passed`
- `recording_timeline_evidence=checked`

Command:

```sh
apps/macos/Scripts/validate-live-passthrough-foundation.sh
```

Result: passed.

Summary line:

- `latency-check: ACCEPTED`

The scripts were updated to include `019` test filters and metadata-only evidence summaries. The long-running hardware gates remain separate evidence files and are not counted as accepted until they are actually run.
