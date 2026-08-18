# Production closeout: `v2026.08.18.1`

## Immutable release

- Tag: `v2026.08.18.1`
- Deployed SHA: `1b166d21eb7164dc2796c23cd380500139b9444c`
- Deploy branch: `codex/release-2026.08.18.1`, fast-forward merged to `master`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.18.1
- Release PR: https://github.com/yshishenya/crisp/pull/5269

## Repository and deployment gates

| Gate | Result |
| --- | --- |
| CD dry-run | pass |
| Exact-SHA full local CI | pass; macOS 693; server 3039 passed / 1 skipped; strict 42 passed / 1 skipped |
| Remote guarded deploy | pass; `deployed_sha` matches release SHA |
| Backup | pass; `/opt/projects/2brain-rec/backups/20260818T103652Z` |
| Restore rehearsal | pass |
| Migration and disposable RLS validation | pass; head `0073_account_auth_linking` |
| Production smoke and readiness | pass; `infra_smoke_ready` |
| Temporal and processing worker readiness | pass |
| Automatic dispatch gate | pass |
| Public health and download smoke | pass; live/ready and package checks returned successfully |
| Guarded rollback | not required |

The deployment recorded `automatic_retry_result`, `backfill_inventory_result`,
`range_playback_result` and `normalization_cleanup_result` as
`required_post_deploy`; these remain separate maintenance follow-ups.

## macOS public release

| Gate | Result |
| --- | --- |
| Developer ID Application / Installer | pass; Team `94N8HYG672` |
| Apple app notarization | pass; `8e1212dd-bf2b-4be3-8efd-dfca8c7c0ed2` |
| Apple package notarization | pass; `21955b94-3612-4514-b8bd-f448726ce91c` |
| Stapler and Gatekeeper | pass for app and package |
| Developer ID → Developer ID Sparkle continuity | pass against `v2026.08.16.7` |
| Local Keychain Sparkle signer | pass; trust generation `1`, custody `ready` |
| Public artifact fetch and update validation | pass; ZIP, PKG, appcast and hashes match |
| Installed production update | pass; `/Applications/GRAF.app` relaunched at `2026.08.18.1` |
| Permission retention | pass; app reports `microphone=granted`, `systemAudio=granted`, `ready=true` |
| Installed Dev channel | pass; `/Applications/GRAF Dev.app`, `pro.2brain.graf.dev`, loopback `127.0.0.1:8081` |

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.18.1.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.18.1.pkg
- ZIP SHA-256: `1edc6f9f4b1715c9ca622b3f70b3b78b67f4b556d206511b89b0ed5672c7892f`
- PKG SHA-256: `1820a2f54b52461cdc194056870d500e5068deb2e6f9d5e27d98da850d44f5f5`
- Appcast SHA-256: `8562827a169f3bf24f185969de4546a59d3c358910cca19d3bb6a761a965a970`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.18.1-20260818T105612Z`

The versioned ZIP, PKG, checksums, notes and signing attestation were copied
before the live appcast. The appcast was replaced last and then fetched again
from the public HTTPS host. Public validation confirmed version `2026.08.18.1`,
enclosure length `6524019`, archive integrity and Sparkle signatures.

## Rollback and limitations

- Rollback restores the previous signed appcast/archive and uses the guarded CD
  rollback runbook; unsigned downgrade through Sparkle is forbidden.
- T099 / #4528 remains open because a real clean-Mac first-grant smoke was not
  performed. No TCC reset, TCC database edit, PPPC profile, driver or virtual
  audio device was used.
- T049 / #4849 remains open because public-link policy is still disabled:
  `share_public_links_enabled=false` and
  `share_public_links_abuse_gate_approved=false`.

All committed evidence is metadata-only and contains no credentials, signed
URLs, raw audio, transcript text or private meeting content.
