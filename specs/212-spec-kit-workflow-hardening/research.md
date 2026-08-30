# Research: Надёжный Spec Kit workflow

## Decision 1: Использовать штатную schema 2 → 3 миграцию

**Decision**: Выполнить один обычный `speckit-bootstrap .` без `--frozen` после dry-run.

**Rationale**: Опубликованный `speckit-bootstrap v0.9.5` сохраняет schema 2 → 3 migration path и project-local integrity state, мигрирует точные промежуточные формы вплоть до `v0.9.4` и fail closed отклоняет mixed, duplicate, surrounding-drift и неизвестные generated states.

**Alternatives considered**:

- Редактировать lock JSON вручную — отклонено: hashes и immutable refs должны вычисляться bootstrap.
- Оставить schema 2 — отклонено: актуальный `doctor` fail closed и не может подтвердить legacy state.

## Decision 2: Не форкать upstream Full SDD Cycle

**Decision**: Оставить upstream workflow управляемым bootstrap и явно ограничить его применение в каноническом GRAF guidance.

**Rationale**: Upstream workflow намеренно содержит шесть общих шагов. Локальный форк быстро разойдётся с upstream, а интерактивные clarify/checklist/taskstoissues и project gates уже надёжно описаны в project guidance.

**Alternatives considered**:

- Изменить `.specify/workflows/speckit/workflow.yml` — отклонено: следующий `workflow update` или bootstrap законно перезапишет managed artifact.
- Добавить второй сложный automated workflow — отклонено: реальной потребности в unattended full GRAF execution нет; guidance и existing skills уже покрывают процесс.

## Decision 3: Тонкий project-specific guard поверх bootstrap doctor

**Decision**: Новый focused guard вызывает frozen `doctor` для generated integrity, затем проверяет только GRAF-specific статические инварианты.

**Rationale**: Это минимальный код без повторной реализации lock hashing, extension validation и skill inventory.

**Alternatives considered**:

- Полностью переписать doctor в repository script — отклонено как дублирование.
- Проверять только Markdown вручную — отклонено: drift уже прошёл незамеченным.

## Decision 4: Project-local skills являются рабочим источником

**Decision**: После миграции хранить generated Spec Kit skills в `.agents/skills`, фиксировать hashes в lock и проверять их doctor.

**Rationale**: Project-local scope исключает случайную зависимость от устаревших `~/.agents/skills` и делает repository workflow воспроизводимым.

**Alternatives considered**:

- Обновлять только глобальные skills — отклонено: разные проекты могут требовать разные locked версии.
- Удалить legacy global skills автоматически — отклонено как разрушительное действие вне scope.

## Decision 5: Community extensions не добавлять

**Decision**: Не устанавливать Spec Inventory, Inventory Alignment, SpecAssay, Security Review или Architecture Guard в этой feature.

**Rationale**: Текущая проблема — drift bootstrap/guidance, а не отсутствие этих функций. Existing GRAF gates уже покрывают security, architecture, checklist и traceability.

**Alternatives considered**: Установить набор новых extensions "на будущее" — отклонено по YAGNI и из-за расширения trust surface.

## Decision 6: Source checkout bootstrap только fast-forward

**Decision**: Обновить чистый `/Users/yshishenya/Documents/speckit-bootstrap` через reviewed PR до опубликованного `v0.9.5`, затем оставить checkout на чистом `main == origin/main`, а immutable tag `v0.9.5^{}` — на release merge SHA.

**Rationale**: Первичная синхронизация до `v0.8.0` открыла общий integrity bug: issue-canon command создавал `.pyc` внутри locked tree. Минимальный bootstrap regression потребовал patch release и совместимого extension pin.

**Alternatives considered**:

- Исправить только GRAF lock — отклонено: будущие bootstrap consumers снова получили бы тот же дрейф.
- Оставить source checkout устаревшим — отклонено: project guidance называет его source of truth для будущих generated-tool changes.

**Validation evidence (2026-08-30)**:

- PR [speckit-bootstrap#30](https://github.com/yshishenya/speckit-bootstrap/pull/30) merged as `ae45a7d241921a19c99d797f3447a4f9284f6d88`; stable immutable release [v0.9.5](https://github.com/yshishenya/speckit-bootstrap/releases/tag/v0.9.5) points to the same commit.
- Release workflow `33322827901` passed package verification and immutable attestations; downloaded binary SHA-256 and installed executable SHA-256 are `b62c8de2b11f8d109710969e1c13a5e8bf2552426012a4c97801eebd04e27a2a`.
- Source checkout is clean on `main == origin/main` at `ae45a7d241921a19c99d797f3447a4f9284f6d88`; tag `v0.9.5^{}` resolves to the same commit.
- Apple notarization and stapling are `N/A`: release asset is a portable shell executable, not a GRAF macOS app/package; its publication gate is the immutable annotated tag, checksummed asset and GitHub attestation workflow above.

## Decision 7: Запретить Python bytecode в locked extension tree у источника

**Decision**: В `github-issue-canon` выставлять `sys.dont_write_bytecode` до импорта shared module во всех трёх command entry points; не исключать `.pyc` из integrity hash.

**Rationale**: Один root-cause fix сохраняет строгую проверку executable tree и закрывает ensure/normalize/validate одновременно. Игнорирование `.pyc` ослабило бы tamper detection.

**Alternatives considered**:

- Исключить `__pycache__`/`.pyc` из hashing — отклонено: executable bytecode останется вне контроля integrity.
- Чистить bytecode после команды — отклонено: crash/interrupt снова оставит tree dirty.

**Validation evidence (2026-08-30)**:

- PR [github-issue-canon#9](https://github.com/yshishenya/spec-kit-ext-github-issue-canon/pull/9) merged as `344713a3d4d10673d3fd984b611ecfdc2c6ce1c8`; stable release [v0.3.2](https://github.com/yshishenya/spec-kit-ext-github-issue-canon/releases/tag/v0.3.2) points to the same commit.
- Release archive SHA-256 is `184e31dc14759ae461318c586545922ea4f2c89493d900891907b15781426e67`.
- GRAF refresh installed `v0.3.2`; validator checked 300 Spec Kit issues, subsequent frozen doctor passed, and no `__pycache__` appeared.
