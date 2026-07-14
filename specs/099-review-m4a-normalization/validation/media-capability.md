# Media Runtime Capability Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Task**: T093

## Command

```text
infra/scripts/test-playback-normalization-container.sh
```

## Result

- `playback_normalization_container_result=pass`;
- Debian Bookworm FFmpeg/FFprobe `5.1.9-0+deb12u1` on arm64;
- profile `review_m4a_aac_lc_48k_mono_64k_v1`;
- validator `playback_validator_v1`;
- runtime user: non-root;
- root filesystem: read-only;
- Linux capabilities: dropped;
- network: none;
- limits: one CPU, one GiB, 128 PIDs;
- work root mode: `0700`;
- non-file protocol: refused;
- full decode: passed;
- synthetic work residue: `0`;
- container residue: `0`;
- image residue: `0`.

## Capability matrix

All 14 cases passed:

- transcode: WAV, MP3, raw AAC, FLAC, Ogg/Vorbis, Ogg/Opus, M4A, MP4,
  MOV, M4V, WebM and MKV;
- byte-identical reuse: already canonical fast-start M4A;
- lossless remux: canonical audio profile with non-fast-start container
  layout.

Every result reached AAC-LC, 48 kHz, mono, non-fragmented fast-start M4A and
passed a complete decode. The probe emitted only versions, fixed case aliases,
capability results and residue counts; it emitted no media content, source
filename, object key, transcript, URL or credential.

## Scope

This proves the isolated media image and dependency/profile capability. It does
not by itself prove a production record, automatic retry, backfill drain,
browser playback or user journey. Feature 097 was not touched.
