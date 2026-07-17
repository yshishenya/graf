# Contract: Update Publication

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
4. Notarize and staple the public app artifact; run Gatekeeper assessment.
5. Create the versioned archive without modifying the signed bundle.
6. Generate and sign appcast/release notes with official Sparkle tools.
7. Validate the appcast, archive length, URLs, signatures, compatibility, and strictly increasing version.
8. Run old-to-new update, rollback/failure, relaunch, and permission-retention smoke.
9. Only then replace the public appcast and add the versioned archive.

Any failure stops before step 9. Private keys, certificates, passwords, notarization credentials, and generated signed artifacts are never committed as source evidence.

## Bootstrap Rule

The first release containing the updater is installed manually once through the existing `.pkg`. Only that release and newer builds can consume this update contract.
