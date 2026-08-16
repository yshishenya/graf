# Quickstart: Проверка процесса от разработки до релиза

## Локальная разработка

```sh
# focused checks — выбираются по затронутому пути
infra/scripts/ci-local.sh --fast
```

Ожидаемый результат: fast lane проходит и фиксируется вместе с commit SHA.

## Release candidate

```sh
infra/scripts/ci-local.sh --full
git rev-parse HEAD
```

Ожидаемый результат: полный CI завершился `ci_local_result=pass mode=full`, а
SHA записан как candidate evidence.

## Production gate (только с отдельным approval)

```sh
infra/scripts/cd-remote.sh --dry-run --branch <branch>
infra/scripts/cd-remote.sh --execute --branch <branch>
```

Ожидаемый результат: dry-run только показывает план; execute повторяет full CI
на pinned SHA и продолжает только после его успеха.

## Negative checks

- Добавить commit после full run: старое evidence больше не относится к HEAD.
- Запустить execute с dirty worktree: deploy должен быть заблокирован.
- Рассматривать interrupted/fast run как full pass: запрещено правилами.
