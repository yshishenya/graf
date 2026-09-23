# Implementation Plan: проверяемое слияние

**Branch**: `276-verify-synced-rebase` | **Date**: 2026-09-24
**Spec**: [spec.md](spec.md)

## Summary

Узко дополнить checked_base: один завершающий sync merge с точной базой и
линейный перенос всех предшествующих изменений. Не общий интерпретатор графов.

## Technical Context

Python 3/stdlib/Git/pytest; macOS/Linux CLI governance; новых зависимостей нет.
Storage: Git objects; merge-tree может создавать недостижимые tree/blob objects,
но не refs, индекс или рабочие файлы. Уже существующий предел count: 1..1000.
Не более линейного числа Git операций по count; без поиска всех историй.
Risk / Validation Lane: significant-feature с high-risk governance review.
Release Gate: exact-SHA governance-fast/macOS/pr-metadata, один frozen release-full,
затем штатные dry-run/execute и Apple gates по отдельному процессу выпуска.

## Constitution Check

До исследования и после проектирования: V/VI PASS; нет ослабления CI,
подписи или full. Полный Spec Kit и независимое requirements/implementation
review обязательны. Продуктовые данные/поведение не меняются; секреты и записи
встреч не читаются. Политика не меняется, поправка конституции не требуется.

## Architecture

Сначала при несовпадении конечных деревьев исключить обход: если source head
имеет больше одного родителя, aggregate-squash ветка недоступна независимо от
длины target range. По имеющимся данным нельзя доказать, что дополнительные
файлы внесены независимым продвижением target, а не подменой replay. Новая
поддерживаемая sync-форма требует равных конечных деревьев. В том числе ранее
принимавшийся aggregate-only squash синхронизированного head при продвижении
target теперь консервативно отвергается; для него нужна синхронизация ветки
и повторная проверка, а не исключение по PR. Линейный source head сохраняет
прежний advanced-target squash. Длины диапазонов не являются сигналом доверия.

При равенстве деревьев новая проверка после прежнего exact squash, до linear-source predecessor:

1. Head имеет ровно двух родителей: source_tip и checked_base.
2. count >= 3: минимум два изменения плюс terminal sync; один replay уже squash.
3. Полный source range checked_base..head имеет ровно count коммитов (чтение
   ограничено count+1). Кроме head, ровно count-1 линейных source commits;
   их predecessor — предок checked_base. Других merge/ветвей нет.
4. Target range ровно count-1 линейных коммитов с predecessor checked_base.
   Итоговый target tree равен head tree.
5. merge-tree --write-tree source_tip checked_base даёт чистый единственный
   tree SHA, равный head tree. Конфликты и ручные добавления sync запрещены.
6. Для каждого source/target по порядку: merge-tree --write-tree
   --merge-base=<source-parent> <target-parent> <source> даёт чистый tree SHA,
   равный target tree. Даже исправленная следующим шагом подмена отвергается.
7. Только после всех сравнений вернуть checked_base. Ошибки Git/объектов/
   неподдержанной версии дают отказ, не запасное разрешение.

Исторический API base может двигаться после слияния; это не доказанная база.
Существующий общий verifier далее связывает recovered base с точными CI
receipts, run/attempt/currentness и metadata без изменений.

## Validation Plan

Настоящие временные Git-репозитории: 3+sync→3; API base advance; wrong
count/base, dropped/extra/reordered replay, tampered intermediate repaired by
final commit, changed final tree, manual sync changes/conflicts, extra source
merge/missing object. Проверить refs/index/files. Старые metadata/event/
source-proof/scope/release consumers сохраняют ожидания. Live read-only common
verifier #7257/#7256/#7267; незавершённый/плохой CI не считается PASS.

## Phases and task outline

T001 положительная регрессия до кода (US1).
T002 отрицательные сценарии (US2).
T003 ограниченная реализация (US1/US2).
T004 consumers/review/converge/fragment/exact-SHA evidence.
Тесты в одном файле, без параллельных правок.
Reviewer сначала читает outline до tasks.md, затем перечитывает tasks до кода.

## Project Structure

scripts/validate-pr-metadata.py; tests/governance/test_pr_metadata_event.py;
specs/276-verify-synced-rebase/; changes/unreleased/F276.yaml.
Новые внешние интерфейсы отсутствуют, contracts не требуются.
