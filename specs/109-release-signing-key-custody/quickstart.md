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

## 3. Protected cloud-channel proof (future lane)

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

## 4. Cloud signing proof without publication (future lane)

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
3. Release a strictly newer signed update through the approved owner-only
   Keychain signer (or the protected cloud lane if it is later re-enabled) and
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
or remote release asset was created or changed. T034 is now the recorded scope
decision; T035 is closed by the physical receipt below, T036 is closed by the
normal-update receipt, and T037 is closed by the owner-only publication receipt
at the end of this document.

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

Решение закрывает исходный T034 как superseded: полноценный protected reviewer
gate недоступен на текущем тарифе и не объявляется настроенным. T035 и T036
закрыты отдельными receipts ниже, а T037 закрыт отдельным owner-only
publication receipt. Текущий release lane использует
только named Keychain signer с явным degraded approval; копия в Bitwarden
остаётся ручным recovery backup и не читается автоматически. Если позже
появится поддержка reviewer approval, cloud-путь можно вернуть без изменения
публичного ключа приложения.

## T034 decision receipt — 2026-07-21

- protected environment `graf-release-signing` и production secret не менялись;
- попытка добавить required reviewer по-прежнему отклоняется GitHub API с
  HTTP 422 на текущем private-repository плане;
- активный public manifest и named Keychain public key уже совпадают по
  metadata-only `keyId`;
- T034 переведён в завершённое состояние решения и superseded закрытие issue;
  bootstrap proof закрыт отдельным T035 receipt, а owner-only release/update
  proof подтверждён в T037;
- в Git, issue и evidence нет приватного ключа, секрета или локального пути.

## T035 physical bootstrap + normal updater receipt — 2026-07-21

Ниже зафиксирован нормализованный metadata-only receipt с контролируемого Mac.
Живые пути, секреты, raw audio и transcript data в Git, issue и evidence не
записываются.

- системный Installer history содержит успешную установку
  `GRAF-trust-bootstrap-2026.07.18.3.pkg` 18 июля 2026 года; PackageKit указал
  bundle `pro.2brain.graf.desktop-app`, версию `2026.07.18.3` и завершил install
  без ошибки;
- перед bootstrap app log показывал установленную версию `2026.07.17.6` и
  `microphone=granted systemAudio=granted ready=true`;
- после bootstrap app log показал `installedVersion=2026.07.18.3` и тот же
  permission state; в receipt нет сброса TCC или повторной выдачи разрешений;
- последующий переход `2026.07.18.3 → 2026.07.20.1` прошёл через обычный
  Sparkle UI: `manual_check_requested`, `user_choice_install`, download,
  `install_requested` и новый `app_update.started`; далее в app log есть
  штатные старты `2026.07.20.2`–`2026.07.20.9` с сохранёнными разрешениями;
- на момент этого T035 receipt публичный appcast содержал только
  `2026.07.20.1`, а установленное приложение — `2026.07.20.2`; поэтому
  повторная проверка через «Проверить
  обновления…» дала `app_update.manual_check_requested` → `app_update.current`,
  корректно не предложила downgrade и новый пакет не ставился;
- текущий bundle `pro.2brain.graf` сохраняет активный public-key id и прежний
  designated requirement; прямые metadata-only TCC checks показывают
  microphone и ScreenCapture `auth_value=2`.

Таким образом, первый переход на новый trust anchor подтверждён единственным
ручным bootstrap, а обычные последующие обновления — штатным Sparkle updater.
T035 закрыт. Публикация двух новых versioned assets подтверждена в T036, а
отдельное owner-only release-attestation подтверждено в T037.

## T036 two normal update receipt — 2026-07-21

Receipt собран только из metadata-only данных GitHub Actions, GitHub Release,
appcast и локального app log; секреты, приватные ключи, живые пути, raw audio и
transcript data не сохраняются.

- workflow `.github/workflows/sign-graf-app-update.yml` run
  [29786274841](https://github.com/yshishenya/crisp/actions/runs/29786274841)
  завершился `success` для `v2026.07.21.1`; validation сначала показала
  `previous=yes archive=no appcast=no`, затем
  `previous=yes archive=yes appcast=yes`, после чего были опубликованы ZIP,
  appcast, checksum и metadata-only attestation;
- [release `v2026.07.21.1`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.1)
  содержит `GRAF-2026.07.21.1.zip`, `graf-appcast.xml` и checksum assets;
  на момент T036 receipt публичный appcast предлагал `2026.07.21.1`;
- первая штатная установка: `2026.07.18.3 → 2026.07.20.1`, события
  `user_choice_install`, download, `install_requested` и
  `app_update.started`, после relaunch — `microphone=granted
  systemAudio=granted ready=true`;
- вторая штатная установка: `2026.07.20.2 → 2026.07.21.1`, события
  `user_choice_install` в `23:14:24Z`, `download_finished`,
  `install_requested` и `app_update.started` в `23:14:34Z`, после relaunch —
  тот же permission state;
- вторая установка завершилась на bundle `pro.2brain.graf`, версии
  `2026.07.21.1`, сохранённым designated requirement и активным Sparkle
  public key. После установки один follow-up download check записал
  `SUDownloadError=2001`, затем ручная проверка вернула
  `app_update.current`; установка и запуск новой версии завершились успешно.

T036 закрыт: две строго возрастающие normal updates прошли через Sparkle,
release assets опубликованы после подготовки архива/appcast, а metadata-only
proof сохранён. Owner-only release attestation подтверждён отдельным T037.

## T037 owner-only publication receipt — 2026-07-21

Это полный metadata-only receipt текущего degraded owner-only lane. Он не
содержит приватного ключа, секрета, живого пути, raw audio или transcript data.

- exact release tag `v2026.07.21.3` имеет remote peeled commit
  `9a17dde2e6938d352cbf38aff7e034a9ad52fad6`, совпадающий с `origin/master` на
  момент staging; GitHub Release опубликован по адресу
  [v2026.07.21.3](https://github.com/yshishenya/crisp/releases/tag/v2026.07.21.3);
- во время подготовки `origin/master` получил docs-only merge-коммиты. Тег
  `v2026.07.21.2` не переписывался, а его release/public assets не
  публиковались, поэтому для фактической
  выкладки выбран следующий свободный higher-CalVer `v2026.07.21.3`;
- active manifest и именованный Keychain `graf-release-signing` совпали по
  `keyId=sha256:63c373b20f82851a6b4443bad2100eede5d50d897ed2aaf9fa8c94db56e4ecce`;
- свежая Keychain attestation прошла локальный verifier с полями
  `checkedAt=2026-07-20T23:54:19Z`, `releaseRef=v2026.07.21.3`,
  `channel=macos-keychain`, `state=ready`, `trustGeneration=1`,
  `workflow=verify-release-signing-custody-local` и тем же commit;
- staging запускался с `GRAF_RELEASE_SIGNING_MODE=keychain`,
  `GRAF_REQUIRE_RELEASE_PROVENANCE=1`,
  `GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK=1` и безопасным approval
  identifier `t037-owner-20260721-3`. Результат helper:
  `signer=keychain`, `custody=degraded`, `published=no`;
- полный `infra/scripts/ci-local.sh` на release train прошёл: 583 macOS-теста,
  1 945 серверных тестов и 34 строгих PostgreSQL-проверки; по одному тесту в
  каждом наборе были штатно пропущены;
- локальные artifacts прошли Sparkle signature verification, owner-only
  update validator, ZIP integrity и package expansion без установки. Версии
  distribution/component/bundle совпали с `2026.07.21.3`, bundle identity
  осталась `pro.2brain.graf`;
- локальный receipt зафиксировал: ZIP `3 669 703` bytes,
  SHA-256 `4aad5495b079f8b075981c8e654820133b315aad417496f143d51e4d15c82a77`;
  pkg `3 464 655` bytes, SHA-256
  `1e27c0ee6b090ac67f53bacb67b97d243b341cfd9d99f7aed67ea71d47cb1c6b`;
  appcast `6 819` bytes, SHA-256
  `6d0dbadeceb066756521b00f80cfc5175e6d7b903445da294bb85ff22d5e2cd0`;
- на public host сначала были загружены versioned ZIP, pkg и checksum, затем
  проверены их remote SHA-256 и ZIP integrity. Предыдущий appcast сохранён как
  recoverable backup, после чего новый `graf-appcast.xml` заменён атомарно;
- повторное публичное чтение всех четырёх файлов прошло: checksum, ZIP,
  appcast signature и archive signature совпали; appcast содержит два item,
  предлагает `2026.07.21.3`, а enclosure length `3 669 703` совпадает с
  публичным ZIP;
- Bitwarden остаётся только offline recovery backup; workflow, приложение и
  public host не читают его и не получают приватный ключ.

T037 закрыт: текущий owner-only release lane доказан реальным подписанным
релизом, публикацией в правильном порядке и повторной публичной проверкой.
Ограничение сохраняется: self-signed owner-only выпуск не является Developer ID
или notarized public distribution; protected reviewer path остаётся будущей
отдельной миграцией.
