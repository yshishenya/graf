# Research: Надёжный Spec Kit workflow

## Decision 1: Использовать штатную schema 2 → 3 миграцию

**Decision**: Выполнить один обычный `speckit-bootstrap .` без `--frozen` после dry-run.

**Rationale**: Опубликованный `speckit-bootstrap v0.8.0` прямо определяет этот путь миграции, сохраняет legacy user-level skills и переводит integrity state на project-local skills.

**Alternatives considered**:

- Редактировать lock JSON вручную — отклонено: hashes и immutable refs должны вычисляться bootstrap.
- Оставить schema 2 — отклонено: `doctor` v0.8.0 fail closed и не может подтвердить состояние.

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

**Decision**: Обновить чистый `/Users/yshishenya/Documents/speckit-bootstrap` через `git merge --ff-only origin/main` до опубликованного `v0.8.0`, не создавая там новый diff.

**Rationale**: Локальный checkout отстаёт на 22 commits, а installed executable уже byte-identical опубликованному tag. Source repository нужно синхронизировать, но менять bootstrap implementation для этой feature не требуется.

**Alternatives considered**:

- Патчить bootstrap source — отклонено: project-specific guidance не является общей обязанностью reusable bootstrap.
- Оставить source checkout устаревшим — отклонено: project guidance называет его source of truth для будущих generated-tool changes.

**Validation evidence (2026-08-30)**:

- Source checkout fast-forwarded from `1974e64e08283ec271032b6b1bd8522082427a6a` to `6019b1b4267292d415c78c9325f2e95555fba9c5`.
- `origin/main` and dereferenced tag `v0.8.0^{}` both resolve to `6019b1b4267292d415c78c9325f2e95555fba9c5`.
- Source and installed executable SHA-256 are identical: `9761c3615d1f506c729053641b0946a2f1d0f8aa5c6a617f01110add8202151a`.
- Checkout remains clean after `git merge --ff-only origin/main`.
