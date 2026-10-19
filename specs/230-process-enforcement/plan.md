# Implementation Plan: Восстановление F230 и границы делегирования

**Branch**: `codex/230-process-enforcement` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)
**Umbrella issue**: #6314. **Base/master SHA**: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.

## Summary

Восстановить источник двадцати исходных задач из issues #6315–#6334, сохранить
двенадцать отменённых дублей и закрыть реальный пробел #6330: явные границы
read-only исследования, исполнения и передачи результата. Нового механизма
управления агентами не требуется: одна секция в существующем scoped runbook.
Полная F230, наблюдательный rehearsal и операторское применение остаются отдельными воротами.

## Technical Context

**Language/Version**: Markdown/JSON/YAML; существующий Python 3.9+ stdlib tooling.
**Primary Dependencies**: существующие Git, gh, Spec Kit, pytest; новых нет.
**Storage**: tracked metadata-only документы; ignored per-worktree pointer.
**Testing**: пять сценариев desk review; существующие context/allocator/governance
checks; независимое reviewer-owned ревью требований и итогового изменения.
**Risk / Validation Lane**: significant-feature, governance: меняется процедура
агентов; docs-only shortcut неприменим. Уточнение обязательно выполнено в spec.
**Release Gate**: no deploy; новый продуктовый выпуск не нужен для процедуры.
Для слияния нужны разрешённый commit, три проверки точного PR SHA/base, review и
отдельное разрешение merge. Полный общий product release остаётся самостоятельным gate.
**Target Platform**: GRAF/Codex на macOS и GitHub; Windows/F200 исключена.
**Project Type**: существующий monorepo; изменение инструкций, не новый сервис.
**Performance Goals**: процедура не добавляет runtime работы или сетевой зависимости;
каждое исследование возвращает ограниченный ответ по назначенному вопросу.
**Constraints**: не менять root AGENTS/CHANGELOG, generic package, workflow,
защиты GitHub, приложение или данные. Сохранить незакоммиченную работу.
**Scale/Scope**: 20 исходных task IDs; 12 отменённых дублей; 8 исполняемых задач.
Главная issue T000 остаётся внешним umbrella, не фиктивной строкой реализации.

## Constitution Check

До исследования и после дизайна: PASS. Конституция 7.1.0 не меняется:
реализуется уже существующий #6330 и соблюдаются её gates, новые принципы не вводятся.

- I–V: продуктовый capture, consent, AI, удаление и публичная подпись не затрагиваются.
- VI: полный порядок Spec Kit, обязательное независимое checklist review,
  analyze до реализации и отдельное разрешение implementation commit сохранены.
- VII: нет пользовательского интерфейса или сторонних материалов.
- Repository hygiene: metadata-only; без секретов и частных путей; один scoped
  источник правил; Legacy Impact untouched; root не меняется.
- Independent reviewer вправе менять только checklist и свой отчёт; checklist
  проверяет качество требований, а итоговый review отдельно проверяет реализацию.

## Validation Plan

1. Подтвердить исходники/статусы 21 issue, хеши источников и все 20 task IDs;
   отменённые строки не превращать в completed tasks.
2. Независимый design review `checklists/governance.md`, затем tasks/analyze;
   после появления tasks повторный review до реализации. Порог Critical0/High0.
3. `speckit-taskstoissues`: только сверить существующие восемь владельцев;
   mandatory issue-canon ensure/validate hooks. Не создавать дубли.
4. Минимально дополнить `docs/agent-guidance/development-process.md` одной секцией.
   Не дублировать текст в root или generic harness; текущая ссылка из root/index уже есть.
5. Ручной разбор пяти случаев из quickstart, независимое итоговое ревью,
   context/process/changelog/governance checks и git diff --check.
6. Прогнать существующие четыре профильных test_* из quickstart. Нового parser
   или теста, проверяющего только буквальный текст инструкции, не добавлять.
7. Converge сверяет весь spec: неполный rehearsal остаётся в T013, финальные
   точные PR/fast ворота в T019. Уже существующие незавершённые задачи не дублируются.
8. После отдельного разрешения commit выполнить финальные проверки на чистом
   exact SHA; GitHub governance-fast/macOS-pr/pr-metadata через общий validator.
   Никакого dirty bypass. Запрос merge и закрытие issue только после полного evidence.

## Project Structure

```text
specs/230-process-enforcement/
  spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md
  recovered-source-index.json, recovery.md
  contracts/agent-assignment.md, contracts/observe-only-rollout.md
  checklists/requirements.md, checklists/governance.md
  validation/review-*.md, validation/agent-delegation-20261016.md
changes/unreleased/F230.yaml
docs/agent-guidance/development-process.md
```

**Structure Decision**: продолжить существующие F230 IDs и scoped runbook.
Portable package уже принят другим владельцем и не требует повторного редактирования.
Операторский отчёт можно подготовить, но отсутствие реального merge_group должно
оставаться явным ограничением. Это не основание отменить требование или включить queue.

## Complexity Tracking

Нарушений нет. Не добавляются dependencies, orchestrator, schema/parser для
простой письменной процедуры, новые aliases/fallbacks или отдельный root-файл правил.
