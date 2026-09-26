# Quickstart: Гигиена дискового пространства Dev-стенда и ускорение CI

**Feature**: 269-dev-storage-hygiene

Проверки выполняются от корня репозитория. Live-сценарии — только на macOS и
только против существующего `GRAF_DEV_STATE_DIR` (стенд `/Applications/GRAF Dev.app`);
отдельные копии приложения не создаются.

## Предварительные условия

- Отсутствует незавершённый переход схемы: `infra/scripts/dev-harness.sh status --json` возвращает `active`.
- Docker Desktop запущен; доступны образы активного манифеста.
- Репозиторий на ветке `269-dev-storage-hygiene`, worktree чист (для live-команд).

## Сценарий 1. Юнит-контракты harness (обязательный, не зависит от стенда)

```sh
python3 -m pytest tests/governance/test_graf_local_adapter.py -q
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=harness/src \
  python3 -c 'from dev_harness.validators import self_test; raise SystemExit(self_test())'
bash -n infra/scripts/ci-local.sh
```

Ожидаемые новые проверки (добавляются в тесты):

- `build` удаляет `build/` и не создаёт `runtime-images.tar`;
- `promote` создаёт архив только для целевого манифеста, удаляет прочие каталоги и теги;
- `prune --dry-run` не изменяет FS и печатает квитанцию по схеме;
- `prune` при `rollback-required`/незавершённом переходе завершается с кодом 2;
- снапшоты перехода удаляются при `complete|recovered` и сохраняются иначе;
- ошибка Docker даёт `status: partial` без падения.

## Сценарий 2. Локальный быстрый лейн (диагностический)

```sh
infra/scripts/ci-local.sh --fast
```

Ожидание: все шаги проходят; в evidence-записи `.dev/ci-evidence/<run-id>.json`
вместо `macos-build` присутствуют `macos-product-*` и `macos-tests` (если
macOS-шаги выполнялись), а `source-revision` привязан к точному HEAD.

## Сценарий 3. Уборка на живом стенде (dry-run → выполнение)

```sh
state="$(infra/scripts/dev-harness.sh status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["state_dir"])')"
infra/scripts/dev-harness.sh prune --dry-run --json | tee /tmp/prune-preview.json
du -sh "$state/artifacts"
infra/scripts/dev-harness.sh prune --json | tee /tmp/prune-result.json
du -sh "$state/artifacts"
```

Ожидание:

- до выполнения: в `artifacts/` не более активного и целевого каталогов; при накопленном
  мусоре dry-run перечисляет его и не удаляет;
- после: суммарный размер `artifacts/` ≤ (архив отката + два приложения + 10%);
- `dev-harness.sh status --json` содержит `retention.rollback_target_id` и остаётся `active`;
- `dev-harness.sh smoke --json --live` — все проверки `pass`.

## Сценарий 4. Откат после уборки (проверка сохраняемости)

```sh
state="$(infra/scripts/dev-harness.sh status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["state_dir"])')"
parent="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["manifest"]["parent_manifest_id"])' <(infra/scripts/dev-harness.sh status --json))"
infra/scripts/dev-harness.sh rehydrate --manifest "$state/manifests/$parent.json"   # если образы выгружены
infra/scripts/dev-harness.sh rollback --dry-run
```

Ожидание: `rehydrate` проверяет все образы целевого манифеста; `rollback --dry-run`
не блокируется. Полный `rollback --live` выполняется только по согласованию
(перезапускает стенд).

## Сценарий 5. CI-кэш и ускорение

1. Push ветки и первый запуск PR: в логах job `Swift build and tests` шаг кэша
   сообщает cache miss; фиксируется длительность.
2. Повторный запуск того же PR без изменений Swift-зависимостей: шаг кэша — hit;
   длительность `swift build` существенно меньше; все шаги и тесты выполняются.
3. Изменение `apps/macos/Package.resolved` (тестовая проверка контракта) приводит
   к смене ключа и cache miss — шаги не пропускаются.
4. На замороженном релизном кандидате `release-full` проходит с тем же кэшем и
   полным набором проверок.

## Откат изменений

- Настройки Time Machine и очистка диска выполняются оператором вручную
  (`tmutil removeexclusion`); в репозитории они не фиксируются.
- Если уборка удалила нужный для расследования каталог, он не восстанавливается —
  восстанавливается только целевой откат (архив + приложение) штатным `rehydrate`.
