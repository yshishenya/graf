# Quickstart: Проверка локальных workflows

## 1. Static policy checks

```sh
test -z "$(find .github/workflows -type f -print -quit 2>/dev/null)"
! rg -n 'workflow_dispatch|\.github/workflows/|dispatch.*workflow|run.*workflow' \
  AGENTS.md docs/agent-guidance infra/scripts apps/macos/Installer/Scripts \
  --glob '!**/test-release-signing-custody.sh'
```

Ожидается: tracked workflow отсутствуют, active guidance не предлагает remote
execution.

## 2. Signing fixture suite

```sh
sh apps/macos/Installer/Scripts/test-release-signing-custody.sh
```

Ожидается: disposable fixtures проходят; private production signer не читается.

## 3. Shell syntax

```sh
sh -n apps/macos/Installer/Scripts/sign-graf-app-update-local.sh
sh -n apps/macos/Installer/Scripts/release-signing-common.sh
sh -n apps/macos/Installer/Scripts/verify-release-signing-custody.sh
sh -n apps/macos/Installer/Scripts/prepare-app-update.sh
```

## 4. Repository gates

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
```

## 5. GitHub setting

```sh
gh api /repos/yshishenya/crisp/actions/permissions
```

Ожидается: `"enabled": false`.

## Excluded live operations

Не запускать реальную release signing команду, `cd-remote.sh --execute`, tag,
GitHub Release publication или production appcast mutation в feature validation.
