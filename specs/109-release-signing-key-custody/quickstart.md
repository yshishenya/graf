# Quickstart: validate custody подписи обновлений

This guide is for controlled test keys and disposable release artifacts.  Do
not put a real private key, raw key export, credential, real meeting data, or
local secret path into terminal history, CI logs, issues, screenshots or this
repository.

See [the contract](contracts/release-signing-custody.md) and
[data model](data-model.md) for accepted inputs and state transitions.

## 1. Static and focused checks

From the feature worktree:

```sh
git diff --check
sh -n apps/macos/Installer/Scripts/prepare-app-update.sh
sh -n apps/macos/Installer/Scripts/provision-release-signing-custody.sh
sh -n apps/macos/Installer/Scripts/verify-release-signing-custody.sh
swift test --package-path apps/macos/Shared --filter InstallerLifecycleEvidenceTests
```

Expected result: scripts are syntactically valid, focused tests pass, and no
tracked source contains a private-key literal, seed, or temporary-key path.

## 2. Local recovery-channel proof

On a disposable controlled Mac, create/use a test Keychain account through the
provisioning command.  Build a test GRAF app using the matching *public*
manifest, then run the custody verifier against that app.

Expected result: the output reports the safe `key_id`, `keychain=ready`, and
does not show private bytes or an absolute secret path.  Repeat with a missing
account and a different test key: each must fail before ZIP/appcast creation.

## 3. Protected cloud-channel proof

For code acceptance, use a separate non-production protected environment with a
disposable test signer. Run `verify-release-signing-custody.yml` manually from
the approved default branch with the test public `keyId`. Download its safe
attestation and pass it to the local verifier. Do not use this test secret to
activate the future production generation.

Expected result: both channels report `ready` only if their derived public
identifiers equal the app and manifest.  A missing secret, wrong secret, stale
tag, or malformed attestation is `unavailable` and cannot be treated as release
success.

## 4. Cloud signing proof without publication

Create a draft release for a disposable tag with a candidate ZIP and Russian
notes.  Dispatch `sign-graf-app-update.yml` with the candidate version, exact
tag and known predecessor version.  The workflow must validate provenance,
identity and key equality, then upload signed artifacts only to the draft.

Expected result: draft artifacts include a ZIP, appcast, checksum and safe
attestation; no production download host or live `graf-appcast.xml` changes.
Repeat with a mismatched signing secret and confirm the job fails before it
uploads a signed appcast.

## 5. Trust-generation migration proof

1. Build and manually install the explicitly labelled bootstrap package on a
   controlled Mac with the old unavailable-key app.
2. Verify GRAF identity, microphone and Screen/System Audio permissions using
   existing permission-retention tools.  Do not reset/regrant TCC permissions.
3. Release a strictly newer signed update through the new protected signer and
   install it through GRAF's normal update UI.
4. Repeat for one further strictly newer update.

Expected result: the bootstrap is the only manual package; both later installs
are ordinary signed in-app updates, preserve the app identity/permissions, and
defer during capture.  A changed key/feed in either ordinary update is rejected.

## 6. Closeout gates

Run the repository gate:

```sh
infra/scripts/ci-local.sh
```

Before a physical release, re-run the release checklist, verify versioned
remote assets and checksums, copy archive/package before `graf-appcast.xml`,
replace the appcast last, then fetch and verify the public result.  Retain the
prior signed feed and publish a higher forward-fix rather than an unsigned or
downgrade rollback.

Before choosing the bootstrap version, wait for any parallel release to merge,
create a clean worktree from exact refreshed `origin/master`, enumerate remote
CalVer tags and choose the next free number.  Do not preallocate or reuse a
parallel release version.
