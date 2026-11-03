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

## Сверка T031 — 2026-10-27

Область: #7120/T031. Полоса этой сверки — `Docs-only / mechanical`:
уточняются существующие доказательства без изменения реализации, требований,
проверок или отметок выполнения. Новые продуктовые прогоны не выполнялись.

Подтверждено чтением GitHub API, журналов и небольших артефактов:

- [PR #7121](https://github.com/yshishenya/graf/pull/7121) слит:
  PR SHA `27419f19b6d0a7c685121b7f84c51f9f31085269`, проверенная основа
  `11097fd18c28b5b0698e4b9d11ad7ea4d5b12e9d`, merge
  `95f3d8f64a43ba3d1a63bc8f406598a1744f7435`.
- `python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr 7121`
  — PASS. Валидатор подтвердил настоящие source proofs и текущие обязательные
  проверки: [governance-fast](https://github.com/yshishenya/graf/actions/runs/35259924029),
  [macos-pr](https://github.com/yshishenya/graf/actions/runs/35259924043),
  [pr-metadata](https://github.com/yshishenya/graf/actions/runs/38807950566).
  Первая macOS-проверка действительно исполнила Swift build/tests;
  отдельный повторный scope-прогон 35259974405 пропустил native job,
  поэтому не считается повторным измерением сборки.
- В macOS-журнале 35259924043 на точном PR SHA записаны `Cache hit for`,
  `Cache restored successfully` и `Cache hit occurred on the primary key`.
- [release-full 35265565925](https://github.com/yshishenya/graf/actions/runs/35265565925)
  — PASS на кандидате `5482d7fb55c89b9ac63b156dfb84fc6a0b373152`.
  Резервация `rc-20260917T193305Z-6f7adc72e514`, authoritative Full,
  receipt и оба компонентных результата согласованы по candidate/SHA/run;
  `skipped_gates=[]`, контрольные суммы компонентов и Full совпадают.
  Кандидат опубликован как
  [v2026.09.17.2](https://github.com/yshishenya/graf/releases/tag/v2026.09.17.2)
  и содержит merge PR #7121. В проверяемых Swift/CI-путях между PR SHA
  и кандидатом нет изменений.
- В macOS-журнале этого Full записаны `Cache not found for input keys`
  и последующее `Cache saved with key`. Основной ключ совпадает с ключом
  PR-прогона: Swift 6.0.3, digest зависимостей
  `572876d2fc17543c4c3985d8595d60ba3fe7f3b20dcf949a2b3cd68a1790c40c`,
  digest исходников
  `41cbadeef4daad4a1877c3ad77b66fb2aff99d7c0a0fd77a550ae6069090bdf3`,
  окончание `-v2`. Это подтверждает работоспособность обоих путей кэша,
  но выпускной прогон случился позже PR и имеет другой набор проверок.

Остаток исходной приёмки T031: сопоставимые первый и повторный PR-прогоны
с исполнением native job, временем и неизменным набором проверок; доказательство
ускорения не менее 30% по SC-004; проверка смены ключа при изменении зависимостей
по сценарию 5. Отдельное сообщение о cache hit или сравнение длительностей
PR и Full этого не доказывает. Эти результаты нельзя подставлять из старого
ключа на SHA `16ccdb6` или из scope-only прогона.

T031/#7120 остаётся открытой. Сверка не принимает всю F269 и не подтверждает
живую уборку/откат T030/#7119; состояние единственного GRAF Dev здесь
не менялось и не проверялось.
