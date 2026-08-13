# Contract: Локальные workflows

## CI

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

Exit `0` означает pass; любое ненулевое значение блокирует PR/release действие.

## Production CD

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
infra/scripts/cd-remote.sh --execute --branch master
```

`--execute` требует отдельного user approval и выполняет full local CI на pinned
SHA перед remote mutation.

## Custody verification

```sh
apps/macos/Installer/Scripts/verify-release-signing-custody.sh \
  --app /path/to/GRAF.app \
  --release-tag vYYYY.MM.DD.N \
  --emit-keychain-attestation /private/path/attestation.json
```

Output attestation создаётся атомарно с mode `0600`, только если named Keychain
signer совпадает с manifest, candidate app и published origin tag.

## Draft update signing

```sh
apps/macos/Installer/Scripts/sign-graf-app-update-local.sh \
  --release-tag vYYYY.MM.DD.N \
  --previous-tag vYYYY.MM.DD.N \
  --candidate-app-asset NAME.zip \
  --previous-app-asset NAME.zip \
  --release-notes-asset NAME.md
```

Команда принимает только safe asset names, clean exact-tag checkout текущего
`origin/master`, draft target release и matching Keychain signer. Она загружает
ровно четыре bounded output assets и не меняет live appcast.
