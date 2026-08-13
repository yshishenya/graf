# Data Model: Локальные release workflows

Feature не добавляет product/database data. Ниже описаны только operational
metadata contracts.

## Local Signing Manifest

- `schemaVersion`: integer `1`
- `status`: `active`
- `trustGeneration`: существующее положительное integer
- `keyId`: `sha256:<64 lowercase hex>`
- `publicKey`: Sparkle Ed25519 public key
- `channels.primary.kind`: `macos-keychain`
- `channels.primary.account`: safe identifier named Keychain account

Private key не является полем и не сериализуется.

## Local Signing Attestation

- `schemaVersion`: integer `1`
- `keyId`: точное значение manifest
- `trustGeneration`: точное значение manifest
- `channel`: `macos-keychain`
- `state`: `ready`
- `checkedAt`: UTC timestamp не старше 24 часов
- `releaseRef`: exact CalVer tag
- `commit`: 40-character origin commit
- `workflow`: `sign-graf-app-update-local` или
  `verify-release-signing-custody-local`
- `evidenceId`: random UUID

## Draft Release Inputs

- Candidate ZIP: safe `GRAF.app/` archive из candidate draft release.
- Previous ZIP: safe `GRAF.app/` archive из predecessor release.
- Release notes: существующий asset с русским пользовательским текстом.

## Staged Outputs

- `GRAF-<version>.zip`
- `graf-appcast.xml`
- `GRAF-<version>.sha256`
- `GRAF-<version>-signing-attestation.json`

Outputs создаются полностью до `gh release upload`. Production feed не входит в
state transition этой feature.

## State Transitions

```text
preflight -> inputs_downloaded -> archives_validated -> signer_attested
          -> staged_locally -> uploaded_to_draft
```

Любая ошибка до `staged_locally` оставляет draft release без новых outputs.
Ошибка upload может оставить только отдельные draft assets; повторный запуск
безопасно заменяет этот bounded output set через `--clobber`.
