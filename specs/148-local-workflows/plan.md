# Implementation Plan: Локальные CI и release workflows

**Branch**: `148-local-workflows` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/148-local-workflows/spec.md`

## Summary

Удалить GitHub Actions как execution layer, сохранить существующие локальные
CI/CD entrypoints и заменить два remote signing workflow одним локальным
fail-closed release script. Sparkle signer остаётся в macOS Keychain; GitHub
используется только для чтения и загрузки draft release assets.

## Technical Context

**Language/Version**: POSIX shell на macOS; существующие Swift 6 helpers

**Primary Dependencies**: git, GitHub CLI, macOS Keychain, Sparkle 2.9.4 tools,
`plutil`, `ditto`, `unzip`, `shasum`

**Storage**: macOS Keychain для private signer; временные локальные directories
для release assets; GitHub Release для draft outputs

**Testing**: shell fixture suite, `sh -n`, repository policy scans,
`infra/scripts/ci-local.sh --fast` и `--full`

**Risk / Validation Lane**: high-risk-feature — меняются release signing,
secret custody и deployment guidance

**Release Gate**: no deploy — feature меняет инструменты и документацию, но не
публикует release и не запускает production CD

**Target Platform**: доверенная macOS release-operator workstation

**Project Type**: self-hosted server + native macOS desktop/release tooling

**Performance Goals**: fast CI остаётся ежедневным коротким feedback loop;
release signing не дублирует полный CI и выполняется один раз на candidate

**Constraints**: private signer не экспортируется; exact tag/SHA; draft-only
upload; metadata-only evidence; production feed не меняется

**Scale/Scope**: три GitHub workflow, один существующий CI entrypoint, один
существующий CD entrypoint и один новый локальный release-signing entrypoint

## Constitution Check

- **Public distribution integrity**: PASS. Developer ID/notarization gates и
  Sparkle public trust generation сохраняются.
- **Secret discipline**: PASS. Новый путь использует Keychain напрямую и не
  переносит private key в environment, файл, GitHub secret или logs.
- **Evidence safety**: PASS. Attestation содержит только public key identity,
  tag, commit, timestamp и random evidence ID.
- **Release provenance**: PASS. Подпись привязана к clean exact-tag checkout,
  текущему `origin/master` и draft release.
- **Rollback/publication**: PASS. Feature не меняет production feed и не
  выполняет deployment.
- **Capture/privacy/deletion**: PASS, вне области изменения.

Post-design re-check: PASS; контракты не ослабляют ни один gate.

## Validation Plan

1. Запустить обновлённый disposable `test-release-signing-custody.sh` с
   негативными archive/provenance/signer/upload fixtures.
2. Проверить shell syntax новых и затронутых scripts.
3. Проверить, что `.github/workflows` не содержит tracked files и активная
   документация не ссылается на GitHub Actions execution.
4. Запустить `infra/scripts/ci-local.sh --fast` перед PR.
5. Запустить `infra/scripts/ci-local.sh --full` как broad security/release
   baseline, поскольку меняется release pipeline.
6. Через GitHub API подтвердить repository Actions `enabled=false`.
7. Production deploy, tag/release publication и реальная подпись исключены.

## Project Structure

### Documentation (this feature)

```text
specs/148-local-workflows/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── local-workflows.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── infra.md
└── tasks.md
```

### Source Code (repository root)

```text
infra/scripts/
├── ci-local.sh
├── cd-remote.sh
└── README.md

apps/macos/Installer/
├── UpdateSigningKey.json
└── Scripts/
    ├── release-signing-common.sh
    ├── verify-release-signing-custody.sh
    ├── prepare-app-update.sh
    ├── sign-graf-app-update-local.sh
    └── test-release-signing-custody.sh

docs/agent-guidance/
├── release-and-validation.md
└── macos-notarization.md

.github/workflows/  # removed as an execution surface
```

**Structure Decision**: reuse existing local CI/CD and signing helpers. Добавить
только один orchestration script для бывшего draft-signing workflow; отдельный
wrapper для CI не нужен.

## Complexity Tracking

No constitution violations or new dependencies.
