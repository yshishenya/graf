# Contract: Update Publication

> The current Apple signing boundary is owned by
> [Feature 130](../../130-developer-id-release/contracts/developer-id-release.md):
> public app/package artifacts require Developer ID, notarization, stapling and
> Gatekeeper. The owner-only section below is archive evidence only.

## Public Locations

- Appcast: `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`
- Full archive: `https://rec.2brain.pro/static/public/downloads/GRAF-<version>.zip`
- Release notes: embedded signed markdown/plain text or a signed HTTPS file under the same approved public surface

The private GitHub repository is not a client dependency.

## Required Inputs

- Exact CalVer without tag prefix: `YYYY.MM.DD.N`
- Developer ID Application identity for public release
- Existing Developer ID signing lineage/team expected by the prior public build
- Sparkle EdDSA private key available outside git to the signing operator
- Corresponding public key supplied to the app bundle build
- Public HTTPS feed URL
- Russian release notes containing changes, validation, compatibility/migration, known limitations, and issue/PR links

## Historical owner-only lane (archive only)

The former controlled-device lane used local/self-signed Apple signing. It is
retained only to explain archived receipts and is not an allowed publication
path. It must not use the public host, GitHub Release or appcast for a new
release.

The exact former command and identity are preserved only in historical receipts.
Do not re-enable `GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST` for a current release.

## Required Artifact Fields

- `sparkle:version`: exact machine-readable CalVer
- `sparkle:shortVersionString`: same user-visible CalVer for this product
- `sparkle:minimumSystemVersion`: `14.5.0` unless an approved release changes it
- `sparkle:hardwareRequirements`: `arm64`
- `pubDate`
- versioned HTTPS enclosure URL
- exact enclosure length
- EdDSA archive signature
- signed appcast/release-note metadata

## Gate Order

1. Build `GRAF.app` and embed the pinned updater framework.
2. Sign nested updater code, framework, then the app with hardened runtime and secure timestamp.
3. Verify bundle ID, app name, version, architecture, nested signatures, team identifier, and designated requirement.
4. For every public distribution, notarize and staple the app and package and
   run Gatekeeper assessment. Local/self-signed, ad-hoc and unsigned artifacts
   fail this gate.
5. Create the versioned archive without modifying the signed bundle.
6. Generate and sign appcast/release notes with official Sparkle tools.
7. Validate the appcast, archive length, URLs, signatures, compatibility, and strictly increasing version.
8. Run old-to-new update, rollback/failure, relaunch, and permission-retention smoke.
9. Only then replace the public appcast and add the versioned archive.

Any failure stops before step 9. Private keys, certificates, passwords, notarization credentials, and generated signed artifacts are never committed as source evidence.

## Apple signing migration rule

When the Apple signing lineage changes from a historical local/self-signed
predecessor to Developer ID, install the notarized Developer ID `.pkg` manually
once and do not replace the appcast. The migration wrapper must report
`publication=manual-pkg-only` and `appcast_staged=no`. Only after that bootstrap
may the ordinary Developer ID → Developer ID Sparkle contract be used.
