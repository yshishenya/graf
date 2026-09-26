# Implementation Plan: Гигиена дискового пространства Dev-стенда и ускорение CI

**Branch**: `269-dev-storage-hygiene` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/269-dev-storage-hygiene/spec.md`

## Summary

Ограничить рост локального Dev-состояния до предсказуемого потолка (один архив
образов целевого отката + два приложения) за счёт переноса создания архива из
`build` в `promote`, удаления каталога сборки после сборки, автоматической
уборки артефактов вне политики, снапшотов завершённых переходов схемы и
остаточных копий приложения; добавить явную команду `prune` с dry-run и
JSON-квитанцией. Ускорить macOS-проверки кэшем SwiftPM в `macos-pr` и
`release-full` и заменить хэширование всего `.build` в доказательствах на явные
продукты сборки.

## Technical Context

**Language/Version**: Python 3 (stdlib) для `scripts/dev-harness.py`; Bash для `infra/scripts/ci-local.sh`; YAML GitHub Actions; Swift 6.0.3 (кэшируемая сборка)

**Primary Dependencies**: Docker CLI / Docker Compose (существующая зависимость); `actions/cache@v4`; существующие pytest и governance-тесты; новых Python-зависимостей нет

**Storage**: `GRAF_DEV_STATE_DIR` (`~/Library/Application Support/GRAF Dev/<repo>/harness`) — файловые артефакты и JSON-метаданные; Docker image store

**Testing**: `pytest tests/governance/test_graf_local_adapter.py`, `tests/governance/test_ci_cd_contract.py`, portable harness self-test, `infra/scripts/ci-local.sh --fast`, live `status`/`smoke`/`prune --dry-run` на стенде

**Risk / Validation Lane**: high-risk product area — затрагивает Docker, retention и rollback контракт (constitution VI перечисляет Docker и retention). Полный Spec Kit с clarify/checklist/analyze; mandatory clarify выполнен (3 уточнения, см. `spec.md`).

**Release Gate**: no deploy — production, нотаризация, подпись и публичное обновление не затрагиваются; release-full прогоняется только как обязательный release-гейт для PR/кандидата

**Target Platform**: macOS (Apple Silicon) для стенда и CI-раннера; Linux-раннеры не выполняют live-сценарии

**Project Type**: moнорепозиторий GRAF: desktop app + server + инфраструктурные скрипты; настоящая фича меняет только Dev-harness, локальный CI и macOS-проверки

**Performance Goals**: архивная часть `artifacts/` ≤ 1 архив отката + 10% после трёх операций; освобождение ≥ 90% мусора при `prune`; повторная macOS-проверка PR с кэшем быстрее холодной не менее чем на 30% при лимите 30 минут

**Constraints**: не менять схему манифеста и формат архива; не удалять данные за пределами `GRAF_DEV_STATE_DIR`; не вызывать глобальные `docker prune`; fail-closed при незавершённом переходе схемы и `rollback_required`; сохранить существующие CLI/JSON-поля; новые проверки не должны уменьшать полноту CI

**Scale/Scope**: ~5 изменяемых файлов кода/инфраструктуры + 2 документа + changelog fragment; один стенд на машину; 174 манифеста и 8 наборов артефактов в текущем состоянии (проверено 2026-09-16)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Проверка | Итог |
|---------|----------|------|
| I. Capture-First MVP Integrity | Фича не касается захвата, маршрутизации, upload, MediaScribe | PASS |
| II. Visible Consent And User Control | Не касается автозаписи, разрешений, видимого управления | PASS |
| III. Plaintext Observability | Не меняет логи/трассы, Langfuse, Temporal; удаляются только машинные сборки | PASS |
| IV. Deletion Truth And Lifecycle Accounting | Удаляются только локальные артефакты Dev-стенда (Docker-образы и каталоги сборки), не пользовательские данные и не записанные встречи; копия удаления остаётся в рамках контроля GRAF | PASS |
| V. Public macOS Distribution And Update Integrity | Подпись, нотаризация, Sparkle и appcast не меняются; архив Dev-образов — внутренний | PASS |
| VI. Spec-Driven Delivery With Testable Gates | Лейн high-risk; clarify выполнен; будут выполнены checklist, tasks, analyze; тесты и quickstart обязательны | PASS |
| VII. Reference-Fidelity Product Design | UI/UX не меняются | PASS |
| Product constraints | macOS Apple Silicon; Docker для инфраструктуры; без новых сервисов и версий | PASS |

Нарушений и требуемых оправданий нет — Complexity Tracking пуст.

## Validation Plan

- **Focused**: `pytest -q tests/governance/test_graf_local_adapter.py` (расширяется тестами политики хранения, prune, квитанции, снапшотов, partial-Docker); portable harness self-test; `bash -n infra/scripts/ci-local.sh`; `python3 scripts/check_spec_kit_governance.py`.
- **Quickstart**: сценарии 1–5 из [quickstart.md](quickstart.md); live-проверка на текущем стенде (`status`, `smoke`, `prune --dry-run`, затем `prune`).
- **Repository gates**: GitHub `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA PR; `release-full` на замороженном кандидате (это изменение CI-контракта, поэтому full обязателен).
- **Deploy gate**: не требуется — production-развёртывание и релиз приложения не затрагиваются.
- **Evidence**: PR фиксирует лейн, команды, результат и SHA; локальные `ci-local.sh --fast` — диагностика, не заменяющая GitHub-гейты.

## Project Structure

### Documentation (this feature)

```text
specs/269-dev-storage-hygiene/
├── plan.md              # Этот файл
├── research.md          # Решения R1–R9
├── data-model.md        # Сущности и переходы состояний
├── quickstart.md        # Сценарии проверки
├── contracts/
│   ├── dev-harness-cli.md
│   ├── ci-workflows.md
│   └── prune-receipt.schema.json
├── checklists/
│   └── requirements.md  # Чек-лист качества спецификации (16/16)
└── tasks.md             # Создаётся $speckit-tasks
```

### Source Code (repository root)

```text
scripts/
└── dev-harness.py                       # retention, prune, жизненный цикл снапшотов и копий

infra/scripts/
└── ci-local.sh                          # привязка доказательств к продуктам сборки

.github/workflows/
├── macos-pr.yml                         # кэш SwiftPM
└── release-full.yml                     # кэш SwiftPM (job macos-full)

tests/governance/
├── test_graf_local_adapter.py           # тесты политики хранения/prune
└── test_ci_cd_contract.py               # контракт CI: кэш, имена артефактов evidence

infra/dev/README.md                      # политика хранения, prune, восстановление
docs/agent-guidance/local-development.md # правила эксплуатации после фичи
changes/unreleased/F269.yaml             # changelog fragment (обязателен по AGENTS.md)
```

**Structure Decision**: изменения локализованы в существующих поверхностях
(harness, локальный CI, macOS workflow, governance-тесты, документация стенда).
Новых модулей и проектов не создаётся; portable-harness (`harness/`) не меняется,
потому что GRAF-специфичная политика принадлежит `scripts/dev-harness.py`.

## Complexity Tracking

Нарушений конституции нет; таблица не заполняется.
