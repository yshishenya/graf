# macOS Notarization And Sparkle Updates

This is the detailed operational recipe for public GRAF macOS releases. Read
it only for a macOS packaging, notarization, or Sparkle-update task; the root
`AGENTS.md` keeps only the gate and this pointer so ordinary sessions do not
load the whole procedure.

## Release boundaries

Backend/GitHub Release and the GRAF Sparkle update are separate publications.
A server tag does not update Sparkle. The live feed must contain a strictly
greater version and a reachable signed ZIP:

```text
https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
```

Public distribution is Developer ID-only: use Developer ID Application for the
app and Developer ID Installer for the package. Notarization, stapling, and
Gatekeeper checks must pass before any public mutation. The historical
`v2026.07.26.6` self-signed `.pkg` is a one-time bootstrap and must not be used
as an ordinary Sparkle update. Local, ad-hoc, and self-signed identities are
for isolated fixtures or historical receipts only.

## 1. Preflight and build

Missing Apple credentials are a publication stop. Check the stored profile
before building:

```sh
xcrun notarytool history --keychain-profile graf-notary
```

Build the signed installer and create the initial ZIP:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
GRAF_UPDATE_FEED_URL="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml" \
GRAF_APP_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
DEVELOPER_ID_INSTALLER_IDENTITY="Developer ID Installer: Your Name (TEAMID)" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh \
  "/tmp/GRAF-YYYY.MM.DD.N.pkg"

ditto -c -k --sequesterRsrc --keepParent \
  apps/macos/RecApp/.build/GRAF.app \
  "/tmp/GRAF-YYYY.MM.DD.N-candidate.zip"
```

## 2. Notarize, staple, and validate

Submit both distribution artifacts, then staple and validate both:

```sh
xcrun notarytool submit "/tmp/GRAF-YYYY.MM.DD.N-candidate.zip" \
  --keychain-profile graf-notary --wait
xcrun notarytool submit "/tmp/GRAF-YYYY.MM.DD.N.pkg" \
  --keychain-profile graf-notary --wait

xcrun stapler staple apps/macos/RecApp/.build/GRAF.app
xcrun stapler staple "/tmp/GRAF-YYYY.MM.DD.N.pkg"
xcrun stapler validate apps/macos/RecApp/.build/GRAF.app
xcrun stapler validate "/tmp/GRAF-YYYY.MM.DD.N.pkg"
spctl --assess --type execute --verbose=4 apps/macos/RecApp/.build/GRAF.app
spctl --assess --type install --verbose=4 "/tmp/GRAF-YYYY.MM.DD.N.pkg"
```

Recreate the ZIP after stapling so Sparkle receives the notarized app:

```sh
ditto -c -k --sequesterRsrc --keepParent \
  apps/macos/RecApp/.build/GRAF.app \
  "/tmp/GRAF-YYYY.MM.DD.N-candidate.zip"
```

Record the Apple request IDs and `Accepted` results in the release receipt.

## 3. Publish the Sparkle update

Before uploading, validate the candidate against the previous Developer ID
app with `apps/macos/Scripts/validate-app-updates.sh`. Create a draft GitHub
Release containing the notarized candidate ZIP, previous ZIP, Russian release
notes, and a metadata-only Keychain attestation. Dispatch
`.github/workflows/sign-graf-app-update.yml` from `master`.

That workflow signs and uploads assets to the draft GitHub Release; it does not
change the production feed. Publish versioned ZIP/PKG files and their SHA-256
checksums on the download host, then replace `graf-appcast.xml` last.

## 4. Closeout

After publication, download the public artifacts again and verify:

- feed version, HTTPS URL, enclosure length, XML, and SHA-256;
- Sparkle signature and `validate-app-updates.sh` against the prior app;
- installed `/Applications/GRAF.app` version matches the live feed;
- app and package pass stapler validation and Gatekeeper.

Keep the evidence metadata-only. Do not commit credentials, signed URLs, raw
audio, transcript text, private meeting content, or private screenshots.

