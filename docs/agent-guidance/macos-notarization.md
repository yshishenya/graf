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

## 0. The one-command path

`apps/macos/Installer/Scripts/release-app-update.sh` runs the whole chain below
and prints a measured duration for every phase. It adds no gate of its own: each
step delegates to the reviewed helper it already had, and the step order is the
order those helpers already require. It never publishes to the public feed.

```sh
sh apps/macos/Installer/Scripts/release-app-update.sh \
  --version YYYY.MM.DD.N --phase prepare
# ... publish the commit and tag; the server release train runs meanwhile ...
sh apps/macos/Installer/Scripts/release-app-update.sh \
  --version YYYY.MM.DD.N --phase publish --verify-feed YYYY.MM.DD.N
```

`--phase all` runs both halves in one foreground chain. `--dry-run` prints the
plan and resolves the Developer ID identities without building, calling Apple,
uploading, or creating a release.

**Why two phases.** The Apple notarization wait is external and cannot be
compressed. `--phase prepare` needs only the clean frozen commit, so it can run
at the same time as the server release train instead of after it; `--phase
publish` needs the published tag and runs afterwards. A release that waits for
the server and then builds the app pays for both in series; split this way the
app is already notarized, stapled, and Gatekeeper-checked when the server side
finishes.

Sections 1-3 below remain the authoritative description of what each phase does,
and stay the manual fallback when a phase has to be run step by step.

## 1. Preflight and build

Missing Apple credentials are a publication stop. Check the stored profile
before building:

```sh
xcrun notarytool history --keychain-profile graf-notary
```

Build the signed installer once from the clean frozen source. The builder keeps
compatible Swift scratch between invocations, still builds both architectures,
and writes the content-bound `<package>.build.json` next to the package:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
GRAF_UPDATE_FEED_URL="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml" \
GRAF_APP_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
DEVELOPER_ID_INSTALLER_IDENTITY="Developer ID Installer: Your Name (TEAMID)" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh \
  "/tmp/GRAF-YYYY.MM.DD.N.pkg"

```

## 2. Notarize, staple, and validate

Run the resumable command with the same app/package produced above:

```sh
python3 apps/macos/Installer/Scripts/release-artifacts.py notarize \
  --app apps/macos/RecApp/.build/GRAF.app \
  --pkg /tmp/GRAF-YYYY.MM.DD.N.pkg \
  --profile graf-notary
```

It submits ZIP and PKG before waiting, saves each Apple request ID immediately,
and polls both requests together. Each Apple command is bounded to 45 seconds;
the overall wait is bounded to 45 minutes and prints progress. After an interruption,
repeat this exact command: a known request is queried, never submitted twice.
Keep the original app/package and build receipt unchanged; rerunning the builder
creates a different signed input and cannot silently replace a submitted build.

The command staples separate copies and validates codesign, stapler and Gatekeeper.
It creates `GRAF-YYYY.MM.DD.N-candidate.zip` after stapling, alongside the final app
and package under the reported `.build/notary/<version>-<source>/final/` directory.
Use these final files for the draft release. The original submitted ZIP/PKG,
`build.json` and `requests.json` remain in the parent directory. A completed retry
checks the same output hashes and public trust without rebuilding or re-stapling.
Record the request IDs and Accepted results in the release receipt.

A lost submit response before the request ID was saved is ambiguous. Do not submit
again or choose the newest item in Apple history. Find the existing ID, inspect
`xcrun notarytool log <ID> --keychain-profile graf-notary`, and require its `jobId`
and `sha256` to bind the saved submitted file. Repeat the command with
`--recover zip=<ID>` and/or `--recover pkg=<ID>`; the helper verifies that binding.
If Apple has not provided such evidence, keep the attempt pending.

The installer/notary and staging locks protect their existing shared directories.
After a crash, establish that the owner has stopped before removing that specific
empty lock directory; never remove a live lock or alter a receipt to force a PASS.
A failed write or fsync is not completed evidence and must be retried/diagnosed.

## 3. Publish the Sparkle update

Before uploading, validate the candidate against the previous Developer ID app
with `apps/macos/Scripts/validate-app-updates.sh`. Create a draft GitHub Release
containing the notarized candidate ZIP and Russian release notes. The previous
ZIP is read from the named previous published release. Give the input candidate
a distinct `*-candidate.zip` name: `GRAF-<version>.zip` is the signed output asset.
From a clean checkout of the exact candidate tag on current `origin/master`, run:

```sh
apps/macos/Installer/Scripts/sign-graf-app-update-local.sh \
  --release-tag vYYYY.MM.DD.N \
  --previous-tag vYYYY.MM.DD.N \
  --candidate-app-asset NAME.zip \
  --previous-app-asset NAME.zip \
  --release-notes-asset NAME.md
```

The local command verifies the named Keychain signer, creates metadata-only
attestation, signs and uploads bounded assets to the draft GitHub Release. It
does not change the production feed. The same command resumes the same version:
checked input/Sparkle archives are cached, all prepared bytes and the original
public attestation stay unchanged, and only missing matching draft assets upload.
Any remote conflict, changed input, expired original 24-hour attestation, or trust
failure stops the attempt before overwrite; there is no `--clobber`. Fresh
Keychain, public/Sparkle validation and both packaged architecture startup checks
still precede upload. `prepare-app-update.sh --verify-only` only validates an
already prepared version and cannot generate or replace it.

After the server deployment, `scripts/release.sh` calls
`infra/scripts/publish-appcast-remote.sh`. It publishes the versioned ZIP first,
replaces `graf-appcast.xml` last, keeps the previous feed as a rollback copy,
and treats a byte-identical repeat as a no-op. The helper validates the signed
feed's exact version, HTTPS enclosure and archive length before SSH mutation.
It does not overwrite the tracked package under `apps/server/src` or the server
runtime `graf.pkg`; those remain under the existing server-CD ownership rules.

## 4. Closeout

After publication, download the public artifacts again and verify:

- feed version, HTTPS URL, enclosure length, XML, and SHA-256;
- Sparkle signature and `validate-app-updates.sh` against the prior app;
- installed `/Applications/GRAF.app` version matches the live feed;
- app and package pass stapler validation and Gatekeeper.

The release driver performs the publication and then the same live-feed check;
for a resumed local signing-only operation, the read-only check remains:

```sh
sh apps/macos/Installer/Scripts/release-app-update.sh \
  --version YYYY.MM.DD.N --verify-feed-only YYYY.MM.DD.N
```

`--verify-feed-only` reads the live feed read-only, requires well-formed XML, requires
the highest feed version to equal the released version, and requires the named
archive URL to be HTTPS and to answer HTTP 200. The publication helper writes
only after its local version/length validation and uses an atomic remote swap.

Keep the evidence metadata-only. Do not commit credentials, signed URLs, raw
audio, transcript text, private meeting content, or private screenshots.
