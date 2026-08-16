# Production closeout: `v2026.08.16.7`

## Immutable release

- Tag: `v2026.08.16.7`
- Deployed SHA: `b9413ededfd1beb1964353edd0935e426e5a3133`
- Deploy branch: `master`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.16.7
- Feature PR: https://github.com/yshishenya/crisp/pull/5212

## Validation decision

The full local gate passed before the release-notes-only commit on the same
runtime code:

- merge SHA `1171b89517ac37c2888fe677d151e86b25c4d273`;
- macOS `685 passed`;
- server `3026 passed / 1 skipped`;
- strict RLS `42 passed / 1 skipped`;
- ContractValidation, lint, compile, Compose and deployment evidence scan:
  pass.

After that gate, only `docs/releases/v2026.08.16.7.md` was added. The exact
deployed SHA is the release-notes commit above. Per explicit release approval,
the production command used `--skip-local-ci`; the interrupted duplicate full
run is not counted as evidence and no second full CI was run.

## Production deployment

| Gate | Result |
| --- | --- |
| CD dry-run | pass |
| Remote deploy | pass; `deployed_sha` matches the release SHA |
| Backup | pass; `/opt/projects/2brain-rec/backups/20260816T204655Z` |
| Restore rehearsal | pass; disposable PostgreSQL and MinIO targets |
| Migration | pass; head `0073_account_auth_linking` |
| RLS validation | pass; disposable PostgreSQL probe |
| Production smoke | pass; `infra_smoke_ready` |
| Temporal/worker readiness | pass |
| Automatic dispatch gate | pass |
| Public health and update feed smoke | pass |
| Guarded rollback | not required |

The deployment command was:

```sh
infra/scripts/cd-remote.sh --execute --skip-local-ci --branch master
```

The CD recorded `automatic_retry_result`, `backfill_inventory_result`,
`range_playback_result` and `normalization_cleanup_result` as
`required_post_deploy`; these are separate maintenance follow-ups and did not
block the release readiness verdict.

## macOS public release

| Gate | Result |
| --- | --- |
| Developer ID Application / Installer | pass; Team `94N8HYG672` |
| Apple app notarization | pass; `3c2fafc0-f25b-47da-9d51-e3618924a282` |
| Apple package notarization | pass; `0fd7e446-bdc6-49e8-acac-a70765bc227c` |
| Stapler and Gatekeeper | pass for app and package |
| Developer ID → Developer ID Sparkle continuity | pass against `v2026.07.26.8` |
| Local Keychain Sparkle signer | pass; trust generation `1` |
| Public artifact fetch and update validation | pass |

Public artifacts:

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.16.7.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.16.7.pkg
- ZIP SHA-256: `d7d5c3027395df910d7daaa2ddb6234595f3363c16fed1a46088ef8fcde6419e`
- PKG SHA-256: `c45855cb78b12b8c68494a873cc73f3498614e35e81d87caf99e7cc99a67c30f`
- Appcast SHA-256: `181b22d7635703c6e597cee691450fe5d0f9c6ea1f64b563e753448eb24ee24a`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.08.16.7-20260816T205817Z`

The versioned ZIP, PKG, checksums, notes and signing attestation were copied
first. The live appcast was replaced last and then fetched from the public HTTPS
host. Public validation confirmed version `2026.08.16.7`, enclosure length
`6491637`, archive integrity and Sparkle signatures.

## Local workflow

- Server: `infra/scripts/start-local.sh`
- Local app: `apps/macos/Scripts/build-local-app.sh --open`
- Bundle ID: `pro.2brain.graf.local`
- Origin: `http://127.0.0.1:8081`
- Login smoke: `local@graf.test` + development code `000000` → `303 /meetings`;
  authenticated `/meetings` → `200`.

The local app is ad-hoc signed and loopback-only by design. It is not a public
distribution artifact and does not enable production OAuth or production
cookies.

All committed evidence is metadata-only and contains no credentials, raw audio,
transcripts or private meeting content.
