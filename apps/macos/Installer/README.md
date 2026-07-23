# GRAF macOS Installer

This directory owns the local app-only macOS installer package.

## MVP Scope

- The local package contains the desktop app only.
- Recording uses app-owned system-audio and microphone capture.
- Normal build, install, update, and uninstall paths do not modify Core Audio
  system components or services.

Silent install, MDM, fleet deployment, and enterprise deployment are out of scope for this feature.

## Local Interactive Installer Build

Use the native Apple `pkgbuild`/`productbuild` flow for local development:

```sh
sudo DevToolsSecurity -enable
spctl developer-mode enable-terminal
sh apps/macos/Installer/Scripts/build-local-installer.sh
open apps/macos/.build/installer/graf-local.pkg
```

By default, the script builds:

- the local SwiftUI app bundle at `apps/macos/RecApp/.build/GRAF.app`;
- a desktop-app component package;
- an interactive product installer at `apps/macos/.build/installer/graf-local.pkg`.

The app bundle and package version use the product CalVer release train without
the git tag prefix: `YYYY.MM.DD.N`. When `GRAF_VERSION` is not set, the script
selects the next same-day CalVer counter from `CHANGELOG.md`. For a deliberate
release candidate, pass the exact version explicitly:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

The matching git tag and GitHub Release add the leading `v`, for example
`vYYYY.MM.DD.N`.

After installing, verify the local result with:

```sh
open "/Applications/GRAF.app"
```

## First Launch on a Mac Without Apple Developer Trust

The no-account local package is not Developer ID signed or notarized. On a
different Mac, Gatekeeper can show a warning such as «Файл graf-local.pkg не
был открыт». This is an expected limitation of the channel, not a reason to
disable macOS security globally.

Use the supported one-time system confirmation:

1. Close the warning dialog without moving the package to the Trash.
2. Open **System Settings → Privacy & Security**.
3. In **Security**, click **Open Anyway** for `graf-local.pkg`, authenticate if
   macOS asks, and confirm the open action.
4. Open the package again and install `GRAF.app` into `/Applications`.

Do not use `sudo spctl --master-disable`, TCC reset commands, manual TCC database
edits, or an audio-driver installer. The package-level signature remains
unsigned in this no-account path even after the one-time confirmation.

After the first launch:

- Click **Разрешить микрофон** in GRAF while the state is «Нужно разрешение» and
  accept the normal macOS prompt. The `.pkg` is not a microphone permission
  target; GRAF must first request access as the running app.
- If the state is «Отклонено», click **Открыть настройки macOS** and enable GRAF
  in **Privacy & Security → Microphone**. GRAF does not promise a second prompt
  after a denial.
- Enable GRAF in **Privacy & Security → Screen & System Audio Recording**, return
  to GRAF, and click **Перезапустить GRAF**. The old process must exit before the
  new process can read the updated permission state.

Local development may use ad-hoc app signing only when Developer Tools Security
is enabled. If it is disabled, macOS can install the `.app` successfully but
kill it through AMFI before app diagnostics are written. Check the local state
with:

```sh
DevToolsSecurity -status
```

## Local Self-Signed Permission-Retention Builds

For owner-machine validation without an Apple Developer account, use a stable
locally trusted code-signing identity such as `GRAF Local Code Signing`. This
path is intended to prove that macOS sees the same `pro.2brain.graf` app
identity across local reinstalls, so granted microphone and Screen/System Audio
permissions do not need to be granted again on every build.

Preflight the local identity:

```sh
security find-identity -v -p codesigning
```

Build explicitly as local-only:

```sh
GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Then inspect the app identity:

```sh
codesign --verify --deep --strict "apps/macos/RecApp/.build/GRAF.app"
codesign -dv --verbose=4 "apps/macos/RecApp/.build/GRAF.app" 2>&1
codesign -dr - "apps/macos/RecApp/.build/GRAF.app" 2>&1
```

Keep the same certificate/private key pair. Recreating a certificate with the
same display name is signing drift and may make macOS ask for permissions
again. Do not commit exported certificates, private keys, passwords, or
generated signed packages.

This local self-signed path is not public release readiness. It does not create
an Apple Developer TeamIdentifier, Developer ID signature, notarization ticket,
or stapled Gatekeeper-ready installer.

Signed pre-release builds must use an Apple application signing identity
(`Apple Development`, `Developer ID Application`, `Apple Distribution`, or
legacy `Mac Developer`). Check available identities with:

```sh
security find-identity -v -p codesigning
```

Then build with:

```sh
GRAF_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

For packaging-only tests on locked-down hosts, use:

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Legacy `TWO_BRAIN_REC_*` environment names are still accepted as fallbacks for
older local runbooks, but new commands should use `GRAF_*`.

Do not run `packagesbuild` for the local installer path. The working local
path is `Scripts/build-local-installer.sh`.

## Signing Policy

- Developer ID signing and notarization are required before public distribution.
- Local certificates, private keys, app-specific passwords, API keys, notarization credentials, and generated signed artifacts must stay outside git.
- Build scripts may reference environment variables or local keychain identities by name, but must not embed secret values.
- Local self-signed app signing is allowed only when
  `GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1` is set. It is accepted for
  single-machine permission-retention validation and an explicitly approved
  owner-only channel for controlled Macs, not for public distribution.
- Public distribution still requires Apple Developer Program access, a
  Developer ID Application certificate for the app, a Developer ID Installer
  certificate when package signing is needed, successful notarization, and
  stapling/verification before release.
- For local development, `build-local-installer.sh` may ad-hoc sign the `.app`
  only when Developer Tools Security is enabled. Apple application signing is
  required for pre-release builds. The product package itself remains unsigned
  unless `DEVELOPER_ID_INSTALLER_IDENTITY` is set in the environment. Unsigned
  packages are acceptable only for local validation.

## In-App Updates

GRAF uses the pinned Sparkle 2 framework for authenticated app-bundle updates.
The existing `.pkg` remains the bootstrap and repair installer. Users on a
build that predates the updater need one final manual `.pkg` installation;
after that, same-identity releases can update `GRAF.app` in place.

The client behavior is deliberately conservative:

- Sparkle checks the stable feed every 86,400 seconds and catches up after the
  app next launches;
- `GRAF > Check for Updates…` starts the same updater manually;
- a trustworthy available release adds `Доступно обновление` to the left
  sidebar in both connected-cabinet and local-only layouts;
- automatic download and automatic installation are disabled;
- scheduled dialogs and relaunch are deferred during active or paused capture,
  recording start/stop, finalization, and termination cleanup;
- no meeting content or system profile is sent with update checks.

Updater-disabled local builds are valid. They embed Sparkle but omit both
`SUFeedURL` and `SUPublicEDKey`; the menu then reports that trusted updates are
unavailable and never opens an unsigned fallback. A configured build reads its
public trust from `UpdateSigningKey.json`:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_APP_SIGN_IDENTITY="Developer ID Application: Example (TEAMID)" \
GRAF_UPDATE_FEED_URL="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml" \
  sh apps/macos/Installer/Scripts/build-local-installer.sh
```

An active manifest contains only the base64 public key, its safe SHA-256
identifier, a trust generation, and the names of the two protected channels.
It is the sole source for `SUPublicEDKey`. Supplying a different public-key
override is rejected; an updater-disabled build remains the only valid build
when the manifest is not active.

### Release-Signing Custody

The signing material itself has two independently controlled copies of the
same generation:

- the normal path is the protected GitHub environment
  `graf-release-signing`;
- the recovery path is the named macOS Keychain account recorded in the active
  public manifest.

The repository, application bundle, issue tracker, public host, logs, and
attestations contain neither signing material nor an export of it. A general
local private-file input is intentionally rejected. The CI path accepts a
temporary runner file only inside the GitHub runner temporary directory, with
mode `0600`, and removes it on exit.

`UpdateSigningKey.json` starts as `unprovisioned`. Do not create a real
generation during ordinary development. At the separately approved release
gate, initialize it once from a clean, reviewed worktree:

```sh
sh apps/macos/Installer/Scripts/provision-release-signing-custody.sh \
  --initialize \
  --keychain-account graf-release-signing \
  --github-environment graf-release-signing
```

This command refuses an existing Keychain generation, sends the transient
export directly to the named protected GitHub environment, deletes the
transient file, and writes only public manifest fields. Review and commit that
public manifest before any bootstrap package. It is not a command for a test
secret: the disposable test workflow uses the separate
`graf-release-signing-test` environment and must never activate the
production manifest.

If an approved initialization is interrupted after its named Keychain
generation was created, do not create a second key or delete the first one.
After checking the owner-approved recovery context, repeat only the protected
transfer with `--resume` and the same account/environment names. It is
idempotent for the cloud secret and activates the same public generation only
while the repository manifest remains `unprovisioned`.

Run `verify-release-signing-custody.yml` manually from the protected
`master` branch and an exact tag. It verifies the tag points to the current
`master` commit, derives only a public fingerprint in the runner, and uploads
a metadata-only attestation. It records only `channel=github-environment`,
`state=ready`, UTC `checkedAt`, key ID, trust generation, tag, commit, workflow
and run ID. The local verifier rejects an attestation dated in the future or
older than 24 hours and emits the current safe Keychain/cloud channel state.
Run this two-channel drill before every production release, at least once every
90 calendar days, and immediately after a change to either control plane;
retain only the timestamp, generation, key ID and channel states. Environment
protections must require independent reviewers, restrict allowed deployment
branches to `master`, and keep the production secret inaccessible to public-host
jobs.

Download that metadata-only artifact through the GitHub Actions interface and
run the local custody verifier against the candidate app, exact tag and
attestation before a recovery-path release. A result of degraded is not normal
readiness: it needs separately recorded release approval plus the explicit
approved-fallback switch, and unavailable always blocks staging or publication.

Before dispatching `sign-graf-app-update.yml`, create a fresh metadata-only
Keychain attestation for the exact candidate tag and attach that JSON file to
the same draft release. The signing workflow requires it as
`keychain_attestation_asset`, checks that it matches the active manifest, tag,
commit and 24-hour freshness bound, then creates the corresponding cloud
attestation before staging. This makes routine staging require evidence from
both protected channels; the Keychain evidence contains no secret or local
machine path and is never copied to the public host.

```sh
sh apps/macos/Installer/Scripts/verify-release-signing-custody.sh \
  --app "/path/to/GRAF.app" \
  --release-tag vYYYY.MM.DD.N \
  --emit-keychain-attestation "/safe/metadata-only-keychain-attestation.json"
```

This mode creates the Keychain evidence only; it is not a release-ready result
until the protected workflow has created the matching cloud attestation.

After the manual bootstrap release, every in-app candidate must keep the same
feed URL and public key as the previous app. Key rotation is a separate approved
multi-release migration; replacing the key or feed in one ordinary update would
strand installed clients and is rejected by the validator.

`build-local-installer.sh` embeds `Sparkle.framework`, adds its runtime search
path, signs Downloader/Installer XPC services, Updater.app, Autoupdate, the
framework, and finally `GRAF.app`. Developer ID builds use hardened runtime and
secure timestamps. The script never relies on `codesign --force --deep` for
signing nested code. The complete pinned Sparkle license and third-party
attributions ship as `Contents/Resources/Sparkle-LICENSE.txt`.

### Validate Identity And Trust

Keep the previous public `GRAF.app` as an immutable comparison input. Validate
the new bundle before creating or publishing update artifacts:

```sh
GRAF_PREVIOUS_APP_BUNDLE="/absolute/path/to/previous/GRAF.app" \
  sh apps/macos/Scripts/validate-app-updates.sh \
  apps/macos/RecApp/.build/GRAF.app
```

Ad-hoc builds can prove only bundle structure and increasing version because
their designated requirement is content-hash based. Public validation is
strict and requires the previous app, the same Developer ID team and compatible
designated requirement, hardened runtime, a valid notarization staple, and
Gatekeeper acceptance:

```sh
GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
GRAF_PREVIOUS_APP_BUNDLE="/absolute/path/to/previous/GRAF.app" \
  sh apps/macos/Scripts/validate-app-updates.sh \
  apps/macos/RecApp/.build/GRAF.app
```

The public app must remain `/Applications/GRAF.app` with bundle identifier
`pro.2brain.graf`, the same Developer ID signing lineage, and permission usage
descriptions compatible with the previous release. Changing a certificate,
team, designated requirement, bundle identity, or install path can make macOS
treat the update as another application and ask for permissions again.

### Stage A Signed Appcast

Write Russian release notes to a file outside generated artifacts, then stage
the archive and signed appcast with the official pinned Sparkle tool and a
matching safe attestation:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_PREVIOUS_APP_BUNDLE="/absolute/path/to/previous/GRAF.app" \
GRAF_UPDATE_RELEASE_NOTES="/absolute/path/to/release-notes-ru.md" \
GRAF_UPDATE_DOWNLOAD_BASE_URL="https://rec.2brain.pro/static/public/downloads" \
GRAF_RELEASE_SIGNING_MODE=keychain \
GRAF_RELEASE_SIGNING_ATTESTATION="/absolute/path/to/safe-attestation.json" \
GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION="/absolute/path/to/safe-keychain-attestation.json" \
GRAF_REQUIRE_RELEASE_PROVENANCE=1 \
  sh apps/macos/Installer/Scripts/prepare-app-update.sh
```

The recovery mode can use only the Keychain account named by the active
manifest. The workflow mode is `ephemeral-ci` and is set only by
`sign-graf-app-update.yml`; it cannot be selected with a general local file.
The helper compares the manifest, candidate app, signer, cloud attestation and
Keychain attestation before it creates a ZIP or appcast. It validates a strictly increasing CalVer,
same-identity inputs, public credential-free HTTPS URLs, Russian notes, archive
metadata, signatures, architecture, and minimum macOS version. It writes
inspectable artifacts only under `apps/macos/.build/updates/` by default. It
does not upload, publish, tag, release, deploy, or alter the public feed.

Production staging must set `GRAF_REQUIRE_RELEASE_PROVENANCE=1`. The helper then
fails closed unless the worktree is clean, `HEAD` equals the published
`origin/master` commit, and the exact `vYYYY.MM.DD.N` tag exists locally and on
`origin` at that commit. It also requires current safe cloud and Keychain
attestations for the exact tag and active trust generation. An untagged candidate may omit this flag for
local validation, but it must never be copied to the production update feed.

If the protected cloud channel is temporarily unavailable, the named Keychain
recovery signer may stage one explicitly approved degraded release only. It
still needs the exact tag/provenance and a fresh Keychain attestation, and the
operator must set both `GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK=1` and
a safe `GRAF_RELEASE_SIGNING_DEGRADED_APPROVAL_ID`. A present but malformed
cloud attestation never falls back silently; it blocks the release. The cloud
workflow itself always uses normal two-channel readiness.

#### Current private-repository mode

The current private repository does not have the GitHub plan capability needed
for a required reviewer protection rule. Until that changes, the approved
release lane is the named macOS Keychain signer in explicit degraded mode. The
owner must provide exact tag/provenance, a fresh metadata-only Keychain
attestation, the degraded-approval flag and identifier, and must copy/version
check the archive or package before replacing `graf-appcast.xml`. Bitwarden is
an offline recovery backup only; CI, the app and the public host never read it
automatically. This mode does not claim that the protected cloud signer is
ready; the manual bootstrap and two-update proofs remain separate receipts and
are not replaced by this lane.

### T037 closeout receipt — `v2026.07.21.3` (2026-07-21)

The current owner-only lane is now proven by a real published release, not only
by local staging. This is metadata-only release evidence; it contains no
private key, secret, local secret path, meeting content, raw audio or transcript.

- The immutable tag `v2026.07.21.3` is peeled to
  `9a17dde2e6938d352cbf38aff7e034a9ad52fad6`, the exact `origin/master` used
  for staging. The [GitHub Release](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.3)
  contains ZIP, pkg, checksums, appcast and the safe Keychain attestation.
- `UpdateSigningKey.json`, the candidate app and the named Keychain account
  `graf-release-signing` agree on key id
  `sha256:63c373b20f82851a6b4443bad2100eede5d50d897ed2aaf9fa8c94db56e4ecce`.
  The fresh attestation is `channel=macos-keychain`, `state=ready`,
  `trustGeneration=1`, `checkedAt=2026-07-20T23:54:19Z` and
  `releaseRef=v2026.07.21.3`.
- Staging used `GRAF_REQUIRE_RELEASE_PROVENANCE=1`,
  `GRAF_RELEASE_SIGNING_MODE=keychain`,
  `GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK=1` and the safe approval
  id `t037-owner-20260721-3`. The helper reported
  `signer=keychain`, `custody=degraded`, `published=no` before publication.
- The full local CI passed on the release train: 583 macOS tests, 1,945 server
  tests and 34 strict PostgreSQL checks, with one expected skip in each set.
  Sparkle signatures, owner-only update validation, ZIP integrity and package
  expansion also passed; the package version and bundle identity are
  `2026.07.21.3` and `pro.2brain.graf`.
- Local SHA-256 evidence is: ZIP
  `4aad5495b079f8b075981c8e654820133b315aad417496f143d51e4d15c82a77`, pkg
  `1e27c0ee6b090ac67f53bacb67b97d243b341cfd9d99f7aed67ea71d47cb1c6b`, and
  appcast `6d0dbadeceb066756521b00f80cfc5175e6d7b903445da294bb85ff22d5e2cd0`.
- On the download host, versioned ZIP, pkg and checksum were copied and
  checked first. The previous appcast was retained as a recoverable backup;
  only then was `graf-appcast.xml` replaced. A fresh public fetch confirmed
  all checksums, ZIP integrity, appcast signature, archive signature, latest
  version `2026.07.21.3`, and enclosure length `3,669,703` bytes.
- Bitwarden remains an offline recovery backup only. CI, the app and the public
  host never read it and never receive the private signing key.

### T037 closeout receipt — `v2026.07.23.11` (2026-07-23)

The Feature 124 macOS update was published through the approved private-repository
Keychain recovery lane after exact tag/provenance and owner-only validation. The
receipt is metadata-only and contains no private key, secret, meeting content,
raw audio or transcript.

- The immutable tag `v2026.07.23.11` points to merge
  `05d66e582f77a4bfeed66057043e8269077d395a`; the [GitHub Release](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.11)
  contains the ZIP, PKG, checksum, appcast, Russian notes and safe signing
  attestation.
- The public feed now reports `2026.07.23.11` and points to
  `GRAF-2026.07.23.11.zip`. The ZIP is `3,734,800` bytes. Local and public
  SHA-256 values are ZIP
  `8abdb294667f5b696373b50aa3583ea0db0bd22b2b865bbad9c3914a85f789df`, PKG
  `d8b93e40164347bfb62f71039fae51fd34dbb84c3c473d21c2268b3edaf2f025`, and
  appcast
  `1eaac01354991f3eedbf0b73e968cedf1fb1ec3641e25b4899b354b6cb1588e7`.
- `validate-app-updates.sh` passed with owner-only trust, the ZIP passed
  integrity validation, and both the appcast and archive passed Sparkle
  signature verification. The previous `2026.07.22.6` archive remains in the
  public directory; the previous appcast was retained as a recoverable backup
  before the new feed was installed last.
- The fresh metadata-only attestation reports `channel=macos-keychain`,
  `state=ready`, `trustGeneration=1`, and the active manifest key id. This
  remains an owner-only local-signing channel, not Developer ID/notarized public
  distribution.

The unused `v2026.07.21.2` tag was not rewritten; its release/public assets
were not published after `origin/master` moved during preparation. The next
free higher CalVer `.3` was used instead. T037 is closed by this receipt. The
remaining limitation is intentional: this is a self-signed owner-only release,
not Developer ID/notarized public distribution; protected reviewer approval is
still a future migration.

For a normal cloud release, first attach the signed candidate-app ZIP,
predecessor ZIP, and Russian notes to a draft GitHub Release. Dispatch
`sign-graf-app-update.yml` manually from `master`; it only reads those
exact-tag draft inputs, checks out the immutable tag, signs into the draft,
uploads the ZIP, appcast, checksums and safe attestation, and serializes
release attempts. These GitHub Release assets stay draft-only until their
review is complete. It has no public-host write command. Verify those draft
assets before changing the live catalog. On the download host copy the
versioned archive and package first, verify their public SHA-256 values against
the reviewed artifacts, and replace `graf-appcast.xml` last. Finally fetch the
public appcast and archive again and verify their version, URL, length, EdDSA
signature, and SHA-256. This ordering prevents an installed client from seeing
a release whose archive is missing or differs from the reviewed artifact.

Before publication, validate the final Developer ID/notarized app, archive, and
appcast together, run an old-to-new update and a rejected/corrupt-update rollback
smoke, and obtain explicit release approval. Keep the previous versioned archive
available during rollout. To halt a rollout, restore the last known-good signed
feed. Macs that already installed the bad release receive a new, strictly
higher-CalVer forward-rollback build containing the reverted code; never offer
a lower version or an unsigned downgrade through the feed. Manual installation
of a prior trusted package is a separately approved recovery path, not the
normal rollback mechanism.

### Owner-Only Self-Signed Channel

When the owner explicitly accepts the absence of Apple Developer ID and every
target Mac is controlled by that owner, the same signed appcast/archive flow may
use `GRAF Local Code Signing`. This is not public release readiness: every new
Mac needs a manual trusted bootstrap, Gatekeeper may warn, and the exact
certificate/private-key pair must remain available.

Run the additional gate against the final staged artifacts:

```sh
GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST=1 \
  sh apps/macos/Scripts/validate-app-updates.sh \
  /absolute/path/to/new/GRAF.app \
  /absolute/path/to/previous/GRAF.app \
  /absolute/path/to/GRAF-YYYY.MM.DD.N.zip \
  /absolute/path/to/graf-appcast.xml
```

The production container reads update files from the ignored host directory
`infra/runtime/public-downloads` through a read-only mount. Copy the versioned
archive and bootstrap package first, then replace `graf-appcast.xml` last so a
catalog never points at a missing archive. Generated signed artifacts and the
private EdDSA key stay outside git.

### One-Time Trust Bootstrap And Recovery

The historic signer cannot be reconstructed. The only supported move to a new
trust generation is a deliberately labelled manual package:

```sh
GRAF_VERSION=YYYY.MM.DD.N \
GRAF_PREVIOUS_APP_BUNDLE="/absolute/path/to/previous/GRAF.app" \
GRAF_UPDATE_FEED_URL="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml" \
  sh apps/macos/Installer/Scripts/build-trust-bootstrap.sh
```

The bootstrap validates the previous and new GRAF identity, permission copy,
signing lineage, unchanged feed URL, and a changed public signing generation.
It writes no appcast and cannot be used by normal staging. Install it manually
once, then prove two strictly higher normal in-app updates. Do not reset or
re-grant macOS permissions for that proof.

If the active generation is suspected compromised, stop public publication,
preserve the last known-good signed feed and versioned assets, and investigate
the scope. A replacement requires a new protected generation, a new reviewed
public manifest, a new manual bootstrap, and then a higher-CalVer forward fix.
Do not rotate a normal appcast key, publish an unsigned downgrade, or silently
reuse an old secret. A secret-pattern guard may occasionally flag safe fixture
text; correct the pattern or fixture so it remains obviously non-secret rather
than adding an exception for a real value.

Moving to Developer ID later is a separate signing-identity migration, not an
ordinary Sparkle update. It requires a new manual bootstrap and may make macOS
ask for permissions again because the designated requirement changes.

### Permission-Retention Proof

On the owner/release test Mac, install and complete two sequential in-app
updates signed by the same identity. Before and after each update run:

```sh
sh apps/macos/Scripts/validate-macos-permission-retention.sh permissions
sh apps/macos/Scripts/validate-macos-permission-retention.sh installed-identity
```

Verify that microphone and Screen/System Audio remain granted, the app
relaunches, capture still starts/stops, and the sidebar marker clears. Never use
`tccutil reset`, edit the TCC database, or re-grant permissions as part of this
proof. Any prompt or identity drift blocks publication.

## Safety Rules

- Updates must not interrupt active capture or an active call.
- The normal uninstaller removes only the GRAF app and its legacy app-name alias.
- In-app archives contain only `GRAF.app`; update, rollback, repair, and
  uninstall do not add or mutate privileged audio components or Core Audio
  services.
- Existing local proof components, if any, are handled only through the separate
  bounded operator procedure in `docs/agent-guidance/legacy-audio-driver-cleanup.md`.
