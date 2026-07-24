# Production closeout: v2026.07.24.11

## Immutable release

- Tag: `v2026.07.24.11`
- Deployed SHA: `e8f6401e8f8fd84c084fec484f7f977ba641705c`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.24.11

## Gates

| Gate | Result |
| --- | --- |
| Local CI | pass |
| Backup | pass (`20260724T210917Z`) |
| Restore rehearsal | pass |
| Migration verification | pass |
| Disposable PostgreSQL RLS probes | pass |
| Production smoke | pass (`infra_smoke_ready`) |
| Automatic dispatch | pass |
| Temporal readiness | pass |
| Processing worker readiness | pass |
| Public live/ready health | pass (`200`/`200`) |

## macOS update artifacts

- Public feed version: `2026.07.24.11`.
- ZIP SHA-256: `81d924ec59ca1c5442d61c83535cdfcde22bab46ca33a8f58a3c2c3d7bedd661`.
- PKG SHA-256: `c4514049922db7ebabe1f01be3dee6b26a06bbb6dcc1130193f0f9391cf8a4c0`.
- Appcast SHA-256: `9de3a4c8fed05bfe503a860f93c7785b160af008ac63933bec8b8fdef2edd1fa`.
- Candidate bundle contains `desktop-cabinet-navigation-back`,
  `desktop-cabinet-navigation-forward` and
  `desktop-cabinet-navigation-reload`; codesign and Sparkle verification passed.
- Signing custody: GitHub environment attestation and named macOS Keychain
  attestation both report `state=ready`, trust generation `1`.

## Rollback reference

Backup `20260724T210917Z` remains the recovery reference. A rollback must keep
the last known-good signed appcast and versioned archive available; never publish
an unsigned downgrade.
