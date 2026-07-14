# Feature 099 Near-Limit Performance Receipt

**Date**: 2026-07-14
**Task**: T102

## Command

```text
infra/scripts/test-playback-normalization-performance.sh
```

## Production-equivalent envelope

- Current `media-runtime` image and production `FFmpegNormalizationPipeline`.
- Non-root worker, read-only root filesystem, no network, all capabilities
  dropped, `no-new-privileges` enabled.
- CPU limit: exactly 1,000 millicores.
- Memory limit: exactly 1 GiB with no additional swap allowance.
- PID limit: 128.
- Worker concurrency represented by one normalization process.
- Configured work budget: 6 GiB.
- Activity timeout: 6 hours.
- Final output cap: 128 MiB.

The fixture was synthetic and deterministic. No user recording, original file
name, media path, object key, transcript, URL, credential or FFmpeg stderr was
written to this receipt.

## Near-limit input and result buckets

| Measurement | Safe result |
|---|---:|
| Source duration | `3h45m_to_4h` |
| Source package | `4608MiB_to_5120MiB` |
| Required source + output cap + reserve | `5120MiB_to_5632MiB` |
| Peak work files | `4608MiB_to_5120MiB` |
| Peak cgroup memory | `768MiB_to_1024MiB` |
| Final output | `96MiB_to_128MiB` |
| Conversion wall time | `185.236s` (`under_10m`) |
| Six-hour activity budget consumed | below 1% |
| OOM / OOM-kill events | `0` |

The synthetic dual-source package stayed below the existing 5 GiB accepted
package limit. Its required-capacity calculation stayed below 6 GiB before
conversion, and monitored work files stayed below 6 GiB for the complete run.

## Media truth

- Production dual-source mix/transcode path exercised: pass.
- Complete source decode: pass.
- AAC-LC, 48 kHz, mono canonical output: pass.
- Fast-start (`moov` before `mdat`), non-fragmented container: pass.
- Complete generated-output decode: pass.
- Output duration aligned with the near-four-hour source: pass.
- Output remained below 128 MiB: pass.

## Capacity preflight regression

The final requirement reconciliation found that the configured budget still
needed an explicit runtime preflight before accepted-source download. The
worker now checks both the per-job logical budget and current free capacity
before download, then reserves output plus cleanup headroom before conversion.
Candidate fallback removes the rejected local candidate before downloading the
authoritative source.

```text
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_failures.py \
  tests/integration/test_playback_normalization_workflow.py \
  tests/unit/test_playback_normalization_worker.py
```

Result: `21 passed, 1 existing deprecation warning in 6.65s`.

Both insufficient real free space and an insufficient logical work budget stop
before source download, create no canonical artifact, preserve the accepted
source, clean the attempt/work directory and enter automatic retry with
`temporary_storage_unavailable`. No user action is exposed or required.

## Cleanup and recovery note

- Final container exit code: `0`; Docker OOM-killed flag: `false`.
- Benchmark container residue: `0`.
- Temporary volume and synthetic media residue: `0`.
- Temporary image-tag residue: `0`.
- The first setup-only attempt stopped before fixture creation because the
  helper had also dropped the `CHOWN` capability. Cleanup returned every
  residue count to zero. The helper was narrowed to one setup-only `CHOWN`;
  the measured worker remained non-root with every capability dropped.

This proves the near-limit conversion fits the selected production resource
and timeout defaults. It does not substitute for the separately completed
Chrome/embedded T100 receipt, production deployment proof, or the separately
deferred feature 097 security scan.
