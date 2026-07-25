# Production closeout: v2026.07.26.1

## Immutable release

- Tag: `v2026.07.26.1`
- Deployed SHA: `669cc6681a24a447efc7aeddf3894e68e7dc822b`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.1
- Feature PR: https://github.com/yshishenya/crisp/pull/4599
- Release PR: https://github.com/yshishenya/crisp/pull/4600

## Gates

| Gate | Result |
| --- | --- |
| Local CI | pass (macOS 639/639; server 2420 passed / 1 skipped; strict PostgreSQL 41 passed / 1 skipped) |
| Contract, lint, compile, Compose and evidence scans | pass |
| Backup | pass (`20260725T214640Z`) |
| Restore rehearsal | pass |
| Migration verification | pass (`0041_share_account_created_email`) |
| Disposable PostgreSQL RLS probes | pass; live production probe not attempted |
| Production smoke | pass (`infra_smoke_ready`) |
| Automatic dispatch | pass |
| Temporal readiness | pass |
| Processing worker readiness | pass |
| Public health | pass (`live=200`, `ready=200`) |

## macOS update artifacts

- Public feed version: `2026.07.26.1`.
- ZIP SHA-256: `7bc7ea785cec887162b7ece0cbfca5812265d7c6abd769c2b0eec5826b426d95`.
- PKG SHA-256: `6e1d4fe1d1a9fa68888bc128169cd9ca757be980f9ab3a2dba8db7ce6c62a547`.
- Appcast SHA-256: `ae3a62d9cb35ccb2692aaad0f0724382b7c297d72989595b7401614538e111c0`.
- Public HTTPS download, Sparkle signature, owner-only trust continuity and
  archive/appcast validation passed.
- Signing workflow: https://github.com/yshishenya/crisp/actions/runs/30175839529
- Signing custody: GitHub environment attestation and named macOS Keychain
  attestation both report `state=ready`, trust generation `1`.

## Rollback reference

The previous appcast remains available at:
`/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.1-20260725T215125Z`.
Versioned previous artifacts remain available. A rollback must publish only a
previously signed appcast and archive; never publish an unsigned downgrade.

The macOS package is signed with the local owner-only GRAF signing identity;
this release is not a public Apple Developer ID/notarized distribution.
