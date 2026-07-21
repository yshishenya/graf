# Production embedded-download hotfix receipt — 2026-07-22

## Release and deploy

- Hotfix PR: [#4217](https://github.com/yshishenya/crisp/pull/4217), merge SHA
  `75783e30cf0a9eac7068aae9a25f0fa8a075b7b1`.
- Release PR: [#4218](https://github.com/yshishenya/crisp/pull/4218).
- Release: [`v2026.07.22.1`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.22.1).
- Release, deployed, and runtime SHA:
  `43f7b09e988621be608049931a048faba1e6a119`.
- Production deploy completed with `deploy_result=pass`; backup, restore
  rehearsal, migration-head, strict RLS, smoke, cleanup, worker, automatic
  dispatch, and readiness gates passed.
- Public `/api/v1/health/live` returned `ok`; `/api/v1/health/ready` returned
  `ready`.

## Application distribution

- The owner-only same-identity GRAF application, ZIP, unsigned bootstrap PKG,
  signed Sparkle appcast, checksums, and metadata-only Keychain attestation are
  attached to the release.
- Public ZIP SHA-256:
  `c3cd2105fc33cb4ce092c78883c284f23f057281baef1d5aa23a02f2700b0c80`.
- Public PKG SHA-256:
  `3a5a06f7148b5f236a81107e48fd3d50719fd0d89bea37cf57414901f5529ec4`.
- Public appcast SHA-256:
  `dd782d2cde859053948544534b1dd27c3a6c61d94a7a4a93616b80083cb7d377`.
- Versioned files were published and checked before the appcast was replaced;
  the previous appcast remains recoverable. Fresh public downloads matched all
  three reviewed hashes, and owner-only update validation passed against the
  previous `2026.07.21.12` application.
- This remains a controlled owner-only locally trusted channel, not Apple
  Developer ID signing, notarization, or public Gatekeeper readiness.

## Installed-app read-back

- The installed application reports `2026.07.22.1`, runs from the canonical
  Applications location, and satisfies its designated requirement.
- A ready owner meeting opened the export dialog and produced one new
  14,654-byte TXT artifact in Downloads.
- After download, the same meeting detail, transcript, and playback timeline
  remained visible; `Раздел недоступен` did not appear.
- Native diagnostics recorded only `cabinet_download_started` and
  `cabinet_download_finished` with safe result metadata. No filename, path,
  meeting identifier, transcript content, or screenshot is committed here.

## Remaining gates

- T060 / [#4216](https://github.com/yshishenya/crisp/issues/4216) is closed by
  the merged, released, and installed hotfix.
- T059 / [#4083](https://github.com/yshishenya/crisp/issues/4083) remains open.
  The controlled owner read-back is not the representative-reviewer usability
  study required by SC-014 and does not turn the preview into a general-release
  claim.
- New meetings remain fail-closed until they receive an explicit accepted
  artifact-policy snapshot.
