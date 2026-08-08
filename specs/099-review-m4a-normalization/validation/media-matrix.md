# Synthetic Media Integration Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Task**: T094

## Command

```text
infra/scripts/test-playback-normalization-integration.sh
```

## Result

- the nested media-container capability matrix passed all 14 cases;
- server integration suite: `56 passed`;
- exit code: `0`;
- elapsed pytest time: `8.82s`;
- `full_decode_gate=pass`;
- `synthetic_residue_count=0`;
- nested container and image residue: `0`;
- one pre-existing Starlette/httpx deprecation warning.

The server suite covers accepted manual upload and first-party boundaries,
automatic scheduling, real FFmpeg workflow execution, supported media matrix,
canonical reuse/remux/transcode and stored canonical publication. It also
confirms that the accepted source remains separate and no conversion occurs in
the user-facing request path.

All generated tones and media containers existed only in disposable temporary
directories or the isolated container. No raw media fixture was written to the
repository and no user/admin conversion action was introduced.

## Scope

This is a local synthetic integration receipt. Authorized `test-rec`, Chrome,
embedded macOS and production closeout remain separate T099-T115 gates.
Feature 097 was not touched.
