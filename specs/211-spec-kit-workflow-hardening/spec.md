# Feature Specification: Надёжный Spec Kit workflow

**Feature Branch**: `211-spec-kit-workflow-hardening`

**Created**: 2026-08-30

**Status**: Draft

**Input**: User description: "Исправить найденный drift Spec Kit, обновить репозитории при необходимости и сделать так, чтобы workflow больше не ломался при обновлениях."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Воспроизводимое обновление Spec Kit (Priority: P1)

Владелец GRAF обновляет Spec Kit через штатный bootstrap и получает согласованный набор CLI, lock state, project-local skills и управляемых файлов без ручного восстановления после обновления.

**Why this priority**: Сейчас CLI, bootstrap lock и фактически используемые skills относятся к разным поколениям, из-за чего `doctor` не может подтвердить целостность установки.

**Independent Test**: На чистой feature-ветке выполнить dry-run, одноразовую миграцию и `doctor`; итоговое состояние должно быть воспроизводимым и повторная проверка не должна выявлять drift.

**Acceptance Scenarios**:

1. **Given** legacy lock schema 2 и актуальный bootstrap, **When** владелец выполняет обычное обновление без `--frozen`, **Then** lock мигрирует в поддерживаемую схему, а пользовательские файлы и legacy user-level skills не удаляются.
2. **Given** завершённое обновление, **When** запускается `speckit-bootstrap . --doctor`, **Then** проверка подтверждает версии, immutable refs, hashes, workflow, extensions и project-local skills.
3. **Given** уже согласованное состояние, **When** bootstrap запускается повторно, **Then** управляемые артефакты остаются идемпотентными и не создают неожиданный tracked drift.

---

### User Story 2 - Полный GRAF SDD-цикл без скрытых пропусков (Priority: P1)

Участник проекта видит один канонический GRAF workflow и не принимает сокращённый upstream workflow за достаточный процесс для significant или high-risk изменений.

**Why this priority**: Установленный upstream `Full SDD Cycle` пропускает обязательные для GRAF этапы, а локальное руководство потеряло финальный `converge`.

**Independent Test**: Проверить project guidance и установленные skills: канонический путь должен явно включать clarify, checklist, analyze, taskstoissues, implement и converge, а сокращённый workflow должен иметь явную границу применения.

**Acceptance Scenarios**:

1. **Given** significant или high-risk изменение, **When** участник читает `AGENTS.md` и `spec-kit-flow.md`, **Then** он получает полный обязательный порядок стадий и не может обоснованно завершить работу до чистого convergence.
2. **Given** custom checklist, **When** начинается implementation, **Then** checkbox state считается reviewer-owned gate и implementation agent не отмечает пункты самостоятельно.
3. **Given** upstream `speckit` workflow из шести шагов, **When** участник выбирает execution path, **Then** руководство прямо запрещает считать его полным GRAF workflow для significant/high-risk lane.

---

### User Story 3 - Раннее обнаружение будущего drift (Priority: P2)

Maintainer получает короткую автоматическую проверку, которая падает при исчезновении ключевых governance-инвариантов или рассинхронизации bootstrap state.

**Why this priority**: Одного исправления текущих файлов недостаточно; следующая генерация или upstream refresh не должна тихо вернуть неполный процесс.

**Independent Test**: Запустить focused governance check в исправном состоянии и затем доказать его чувствительность контролируемыми test fixtures или изолированными негативными сценариями.

**Acceptance Scenarios**:

1. **Given** корректный repository state, **When** запускается focused check, **Then** он подтверждает полный порядок стадий, reviewer ownership, актуальный lock schema и project-local skills.
2. **Given** отсутствующий `converge`, reviewer-owned marker или несовместимая lock schema, **When** запускается focused check, **Then** он завершается ненулевым кодом и называет нарушенный инвариант.
3. **Given** обновление upstream Spec Kit, **When** maintainer выполняет bootstrap и focused check, **Then** несовместимое изменение обнаруживается до merge.

### Edge Cases

- Upstream latest tag недоступен из-за сети: существующий frozen state остаётся пригодным для диагностики, но обновление не объявляется завершённым.
- Legacy user-level skills существуют одновременно с project-local skills: миграция сохраняет legacy copy и явно сообщает о ручной последующей уборке, не удаляя пользовательские данные.
- Рабочее дерево содержит пользовательские изменения: обновление не должно сбрасывать или перезаписывать их без review.
- Upstream workflow остаётся сокращённым: project guidance продолжает определять более строгий GRAF flow.
- Локальная конфигурация extension создаёт `local-config.yml`: файл остаётся machine-local и не попадает в Git.
- Upstream меняет формат templates или bootstrap anchors: проверка должна fail closed с понятным сообщением вместо молчаливого частичного обновления.

## Scope

### In Scope

- GRAF repository governance, bootstrap state, generated project-local skills, ignore rules, focused validation и changelog.
- Локальный source checkout `yshishenya/speckit-bootstrap`, если он отстаёт от собственного опубликованного stable release.
- Совместимость с актуальным stable GitHub Spec Kit `v1.0.1`.

### Out of Scope

- Установка необязательных community extensions или presets.
- Изменение продуктового runtime GRAF, production deployment или новый product release.
- Удаление legacy user-level skills без отдельного явного решения пользователя.
- Переписывание upstream GitHub Spec Kit или публикация нового bootstrap release без отдельной необходимости и validation evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Проект MUST фиксировать актуальную stable версию Spec Kit, immutable source ref и согласованную bootstrap lock schema.
- **FR-002**: Одноразовая миграция legacy bootstrap state MUST выполняться без `--frozen`, сохранять пользовательские файлы и не удалять legacy user-level skills.
- **FR-003**: Все используемые Spec Kit skills MUST быть project-local, входить в lock integrity state и проверяться командой `doctor`.
- **FR-004**: Управляемый `.specify/.gitignore` MUST исключать `.specify/feature.json` и `extensions/*/local-config.yml`, не скрывая shareable governance artifacts.
- **FR-005**: Канонический GRAF flow MUST включать `specify → clarify → plan → checklist → tasks → analyze → taskstoissues → implement → converge` перед соответствующими validation/release gates.
- **FR-006**: Custom checklist MUST быть reviewer-owned; генерация оставляет новые пункты unchecked, а implementation читает marker state и не меняет его.
- **FR-007**: Сокращённый upstream workflow MUST NOT описываться как достаточный для significant/high-risk GRAF lane.
- **FR-008**: После implementation MUST выполняться append-only convergence loop до результата без оставшихся обязательных задач.
- **FR-009**: Focused validation MUST fail closed при потере `converge`, reviewer ownership, project-local skills или поддерживаемой lock schema.
- **FR-010**: Повторный bootstrap MUST быть идемпотентным для управляемых tracked artifacts либо явно объяснять ожидаемый diff.
- **FR-011**: Локальный source checkout `speckit-bootstrap` MUST быть fast-forward синхронизирован с опубликованным stable source, если он отстаёт и не содержит локальных изменений.
- **FR-012**: Изменение MUST обновить `[Unreleased]` changelog и зафиксировать validation evidence без секретов и приватного содержимого.

### Key Entities

- **Bootstrap lock state**: Schema version, bootstrap version, Spec Kit version/ref, extension/workflow versions and hashes, project-local skill hashes.
- **Project-local skill set**: Generated Codex skills used by this repository and validated against the lock.
- **Governance invariant**: Required workflow stage, ownership rule or compatibility boundary that focused validation must enforce.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `speckit-bootstrap . --doctor` completes successfully after the one-time migration.
- **SC-002**: Lock state records schema 3, Spec Kit `v1.0.1`, its immutable ref, and hashes for every project-local Spec Kit skill.
- **SC-003**: A second bootstrap run followed by `git status --short` produces no unexplained tracked governance drift.
- **SC-004**: Focused validation detects 100% of the four protected failure classes: missing convergence stage, missing reviewer ownership, missing project-local skills and unsupported lock schema.
- **SC-005**: Canonical project guidance contains one unambiguous full GRAF sequence and an explicit boundary for the shorter upstream workflow.
- **SC-006**: No product runtime, production configuration, deployment state, optional community extension or user-owned legacy skill is changed outside the declared scope.

## Assumptions

- `v1.0.1` remains the latest stable upstream release during this change; live resolution is rechecked before migration.
- The published `speckit-bootstrap v0.8.0` is the current stable source for schema 3 migration.
- Existing GRAF product gates and issue canon remain authoritative and are extended, not replaced.
- A clean disposable feature worktree is the implementation surface; master and unrelated worktrees remain untouched.
