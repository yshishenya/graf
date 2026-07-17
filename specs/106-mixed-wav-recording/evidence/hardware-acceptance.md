# Installed-App Hardware Acceptance

**Status**: open — no result is invented.

## Preconditions still required

- The exact `v2026.07.17.6` baseline tag and commit SHA are verified as
  `4be444e82ec449a3bb5312920fb0cd6008072c56`.
- The local install and controlled hardware procedure require separate approval.
- The user-confirmed, still-in-progress parallel `v2026.07.16.7` work must
  not be used as the baseline or merged into this feature.

## Non-install candidate proof

- A local-only `2026.07.17.10` candidate was built from
  `d9d4d6f7970bb21f20cc2d2a66bde1f850d2e9da` with the stable owner signing
  identity. Its strict owner-only update validator passed against the
  separately installed `2026.07.17.9` app with designated-requirement
  continuity and the same configured public update contract.
- The local package intentionally has no Developer ID package signature and is
  not notarized. No installation, launch, recording, hardware measurement or
  release action was performed, and the parallel installed app was left
  untouched.

## Required future metadata-only verdicts

- 60-minute v5 timeline, route and incoming-level check;
- exact package member/format/hash-count/duration checks;
- user-visible intermediate progress, one-job processing, playback and
  transcript status;
- deletion and rollback of one subsequent controlled recording.

Do not add audio, decoded media, marker text, transcript text, device name,
private path, credential, signed URL or provider payload to this file.
