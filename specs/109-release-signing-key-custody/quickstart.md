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
sh apps/macos/Installer/Scripts/test-release-signing-custody.sh
swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests
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
disposable test signer. Run the custody verification workflow manually from the
protected master branch with the test public key identifier and an exact current
tag. Download its safe attestation and verify only its safe fields and the
workflow result; do not pass a test-environment attestation to the production
local verifier. Do not use this test secret to activate the future production
generation.

Expected result: the protected test workflow reports matching, missing and
mismatched test-secret states without production activation. The production
local verifier may report both channels `ready` only after the active production
manifest, candidate app, named Keychain recovery signer and current production
attestation agree. A missing secret, wrong secret, stale tag, malformed or
expired attestation is `unavailable` and cannot be treated as release success.

## 4. Cloud signing proof without publication

Create a draft release for a disposable tag with a candidate-app ZIP,
predecessor-app ZIP, Russian notes and a fresh metadata-only Keychain
attestation for that exact tag/commit. Dispatch the draft-signing workflow from
protected master with the candidate version, exact tag, known predecessor and
Keychain-attestation asset name. The workflow must validate provenance,
identity, manifest, both channel attestations and key equality, then upload
signed artifacts only to the draft.

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

## T014 disposable-artifact receipt — 2026-07-20

On the refreshed `origin/master` base, the required local-only validation used
only the repository's disposable public fixture and a locally self-signed
package. No production signing generation, protected environment, release tag,
installed app, TCC permission, public appcast, or remote asset changed.

- `apps/macos/Installer/Scripts/test-release-signing-custody.sh` passed with
  `fixture=disposable-public`.
- `apps/macos/Scripts/validate-macos-permission-retention.sh preflight`
  confirmed the local validation signing identity is available.
- `apps/macos/Scripts/validate-macos-permission-retention.sh build` created a
  local validation package only; its own output confirms it is neither
  Developer ID signed nor notarized for distribution.
- `apps/macos/Scripts/validate-macos-permission-retention.sh staged-identity`
  confirmed bundle identifier `pro.2brain.graf`, a valid local signing
  authority, and a designated requirement for the staged disposable app.

This proves the local/disposable boundary required by T014. Physical bootstrap
installation, TCC-retention proof, protected environment enrollment, and
normal in-app update proofs remain separate open tasks.

## T023/T027 fail-closed simulation receipt — 2026-07-20

The US3 failure matrix was run with metadata-only attestations, a disposable
signed-app pair supplied only at runtime, and a temporary staging directory.
The command path was:

```sh
GRAF_RELEASE_SIGNING_CANDIDATE_APP_BUNDLE=<disposable-candidate-app> \
GRAF_RELEASE_SIGNING_PREVIOUS_APP_BUNDLE=<disposable-previous-app> \
apps/macos/Installer/Scripts/test-release-signing-custody.sh
swift test --package-path apps/macos --filter InstallerLifecycleEvidenceTests
```

The receipt was:

- stale attestation: blocked before staging, digest unchanged;
- wrong release/commit attestation: blocked before staging, digest unchanged;
- missing draft app bundle: blocked before staging, digest unchanged;
- concurrent staging lock: blocked, digest unchanged;
- forward-rollback request against a higher staged version: blocked, digest unchanged;
- `InstallerLifecycleEvidenceTests`: 18 passed;
- custody harness: `release-signing custody tests passed`, fixture remained
  `disposable-public`.

No production key, GitHub environment, release tag, public appcast, remote
asset, installed app, TCC permission, audio or transcript data was changed.

## T033 release-provenance receipt — 2026-07-20

After explicit release approval, the refreshed `origin/master` was checked in a
clean detached release worktree. The metadata-only receipt is:

- `origin/master` and the detached `HEAD` both resolve to
  `b23950053a09c6e395a5742d3d8a9e5f2a67a910`;
- the newest remote CalVer tag is `v2026.07.20.7`, targeting
  `0036ff5ce3bca7eff9f822389fa897c02966b34f`, and the refreshed
  `origin/master` is its ancestor;
- the next free version strictly greater than `.12` is `v2026.07.20.8`, and
  the remote tag check confirms that candidate is absent.

No tag, package, active-key enrollment, protected environment, public appcast,
or remote release asset was created or changed. T034–T036 remain separate
release gates.

## Решение для приватного репозитория без платного GitHub — 2026-07-20

Required reviewer нужен не для работы GRAF, а как ручной предохранитель перед
доступом CI к приватному ключу Sparkle. Установленное приложение принимает
обновление только с подписью соответствующего ключа, поэтому утечка ключа
позволила бы выпустить доверенное вредоносное обновление.

Репозиторий остаётся приватным, платный GitHub-тариф и публикация исходников не
используются. Environment `graf-release-signing`, его secret и branch policy
`master` уже существуют, но GitHub API отклоняет добавление required reviewer с
HTTP 422, потому что текущий тариф не поддерживает такую protection rule.

Принятый бесплатный fallback:

- автоматический cloud signing и обычная публикация через GitHub Actions не
  считаются доступными;
- редкий owner-only выпуск выполняется локальным macOS Keychain signer через
  существующий `GRAF_RELEASE_SIGNING_MODE=keychain` путь;
- такой выпуск остаётся явно `degraded`: нужны exact CalVer tag/provenance,
  свежая Keychain attestation и явное owner approval; архив и appcast проверяются
  локально, а публикация выполняется вручную в порядке archive-before-appcast;
- значения секретов, приватные ключи и credential-bearing URLs в репозиторий не
  записываются.

Это не закрывает T034: полноценный protected reviewer gate отсутствует. T035 и
T036 не объявляются выполненными по этому fallback. Если позже появится CI с
бесплатным ручным approval и внешним secret manager, protection можно вернуть в
нормальный двухканальный режим без изменения публичного ключа приложения.
