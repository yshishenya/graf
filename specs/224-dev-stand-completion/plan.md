# Implementation Plan: единый безопасный стенд GRAF Dev

**Branch**: `codex/224-dev-stand-completion` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)
**Input**: восстановленные требования #6180–#6188.
**Status**: US1 локально реализована и проверена; принятие PR и T008 ещё открыты. Исходный проект и ограничения места ниже относятся к16.10.2026; текущие условия — в validation.md.

## Summary

Привязать один канонический GitHub repository к существующему физическому
состоянию GRAF Dev без переноса файлов или замены promote.lock. Одноразовая
adopt-state подтверждает исторического владельца; неизвестная принадлежность
останавливает shared операции. Основной runtime/lifecycle/schema механизм уже
существует и повторно не строится. Полный объём #6180 сохраняется: US2/US3
принимаются отдельно; принятие принадлежности не завершает общую задачу.

## Technical Context

**Language/Version**: Python3, штатные Git/macOS инструменты.
**Primary Dependencies**: существующие subprocess, urllib.parse, re, json,
fcntl, pathlib, tempfile; текущие pytest/Git. Новых зависимостей нет.
**Storage**: существующее файловое состояние harness; одна машинная binding
запись и краткая registration lock. Operational promote.lock остаётся прежним.
**Testing**: существующие governance tests, новые временные Git repos и
межпроцессные проверки; mocks внешних воздействий, без живого приложения.
**Risk / Validation Lane**: high-risk product area (инфраструктура, общее
состояние, восстановление и разрешения); pointer high-risk-product.
**Release Gate**: no deploy. Commit после validation и отдельного разрешения;
merge/release/deploy отдельно. Реальный adopt-state пока не выполняется.
**Target Platform**: один macOS GRAF Dev; изолированные проверки переносимы.
**Project Type**: существующий инструмент локальной разработки.
**Performance Goals**: отсутствие пересечения критических секций; определение
принадлежности без сети, копирования данных и сборок.
**Constraints**:27 GiB свободно; крупные сборки запрещены, стенд занят.
**Scale/Scope**: одна машина, один Dev, несколько worktrees/clones/processes.

## Constitution Check

До Phase0: PASS для исследования. Конституция7.1.0 прочитана; mandatory clarify
зафиксирован в spec.md, открытых продуктовых вопросов нет. Сохраняются один Dev,
подпись, разрешения, данные и production boundary, metadata-only evidence.
Новые принципы не требуются. Реальная смена занятого стенда не входит в этот шаг.

После Phase1: архитектура US1 сохраняет исходное состояние и operational lock,
не изменяет frozen code/guard, не добавляет зависимость/alias/fallback/workflow.
Изолированные проверки не управляют общими образами. Полный independent
checklist PASS, analyze и issue sync ещё обязательны до реализации.
Это архитектурная проверка, а не заявление о прохождении этих ворот.

## Phase0: Research

Завершены два независимых исследования: принадлежность/все callers и широкие
обязательства #6180. Решения, источники и отвергнутые варианты: [research.md](research.md).
Данные: [data-model.md](data-model.md); контракт: [contracts/state-ownership.md](contracts/state-ownership.md).

Ключевой результат: legacy state не хранит origin, поэтому автоматический
переезд на новый hash-root недоказуем и небезопасен. Явная неизменяемая machine
binding сохраняет прежний root и inode lock. Для старых adapters нужна
предварительная проверка их resolver без изменения guard; независимые clones
сопоставляются по строгому canonical origin при сохранении exact-byte gates.
Ограничение самостоятельного старого controller записано явно, не скрыто.

## Phase1: Current Slice US1

1. Минимальные функции остаются в scripts/dev-harness.py: strict origin,
   binding/path preflight, adopt-state; повторно используются _write_json и
   существующий lock/validation flow. Нет нового пакета/manager abstraction.
2. Одна machine binding неизменяема после регистрации. Registration lock
   используется только для регистрации; общий operational lock не переезжает.
   Публикация binding допускает безопасный повтор после прерывания.
3. Операции разрешают shared effects только по binding до side effects;
   после ожидания lock повторяется ownership/active-parent check. Isolated
   override — только временные файловые операции без общих Docker tags.
4. _checkout_adapter сохраняет clean/fullSHA/tracked-byte/digest gates;
   дополнительно проверяет canonical origin и resolver закреплённой версии
   в ограниченном subprocess до первого stop/install/Docker mutation.
5. infra/dev/README.md и scoped local-development guidance описывают одноразовое
   принятие, отказ неоднозначных roots, запрет самостоятельных старых scripts,
   ограничения снимка status и fixture prune. Root AGENTS.md не меняется.

## Оставшиеся истории и их владельцы

US2: отдельная проверка фактического одного процесса и всех компонентов по
точному SHA, с остановкой обязательной службы. Существующие lifecycle и
immutable-image primitives используются без повторной реализации.

US3: отдельный минимальный срез обычного promote crash recovery. Исследование
обнаружило отсутствие durable journal до stop/install; сначала воспроизводящий
отказ, затем отдельный уточнённый дизайн фаз/восстановления и reviewer gate.
Текущий план принадлежности не разрешает код US3 и не объявляет её готовой.
Совместимый живой rollback и Dev TCC до/update/relaunch/после остаются открытыми.
Миграция уже имеет F249 T038/#6786; новый дубликат не создаётся.

## Validation Plan

[quickstart.md](quickstart.md) задаёт исходные70PASS и отрицательный probe,
полную изолированную матрицу US1, процессные проверки старого lock/adoption,
неизменности данных и inode, unsafe paths/origin, frozen checkout и fixture prune.
Новым проверкам сначала нужен воспроизведённый отказ исходного кода.

После реализации US1: focused matrix, независимое implementation review,
ограниченный converge, process/context/changelog/governance/diff. Затем отдельное
разрешение на commit/draft PR; governance-fast, macos-pr, pr-metadata на exact
SHA/base. Исходная T008 требует bounded --fast на неизменном SHA: выполнять
после разрешённого коммита на подходящей машине, без самовольной крупной
сборки при27GiB; результаты не подменять одним focused набором.

Полный CI — один GitHub release-full на frozen candidate; реальные macOS,
rollback/TCC и live adoption после согласованного освобождения стенда и
достаточного места. Эти проверки пока не состоялись и не закрывают #6180.

## Project Structure

- `scripts/dev-harness.py` — текущие операции и минимальные ownership helpers.
- `tests/governance/test_dev_harness.py`, `test_graf_local_adapter.py` — reuse
  поведения; отдельный `test_dev_state_ownership.py` для изолированной матрицы
  origin/binding/процессов, чтобы не раздувать прежние suites.
- `specs/259-audit-remediation/evidence/dev-identity-probe.py` — существующий
  независимый probe: сохранить смысл отрицательных случаев при новом resolver.
- `infra/dev/README.md`, `docs/agent-guidance/local-development.md` — один штатный путь.
- `changes/unreleased/F224.yaml` — собственный фрагмент проверенного изменения.
- `specs/224-dev-stand-completion/` — восстановленные требования и доказательства.

## Complexity Tracking

Нарушений конституции/новых слоёв нет. Registration lock необходим, потому что
два разных roots ещё не имеют общей operational lock до регистрации; после
регистрации их выбор исключён, и сохранённый promote.lock остаётся единственным
правом менять стенд. Ограничение старого кода является эксплуатационной границей,
а не основанием для обхода или обещания недостижимой защиты.


## Уточнение трёх замечаний PR7676 — 21.10.2026

Текущие T003/T004/T005/T008 охватывают ошибки4313857009,4313857014,4314313869.
До исправления нужны независимое ревью требований и воспроизводящие отказы.
Adopt-state отклоняет нестандартный GRAF_DEV_INSTALL_PATH до регистрации,
даже если приложение остановлено; сравнивается выбранный путь с DEV_APP_PATH,
поиска других приложений по диску нет. Общий _load_active проверяет runtime_mode
по фактически выпускаемым значениям live/metadata-only до использования
указателя; повреждённое/отсутствующее значение не означает безопасный режим.
Изолированная launch fixture задаёт собственную canonical repository identity
через monkeypatch _repo_identity; реальные строгие Git-проверки остаются
в ownership suite. Нужны отрицательные adoption случаи с сохранностью
файлов/lock inode/отсутствием binding, положительные допустимые режимы и
launch suite без ambient origin. Продукт/Dev/общие данные не запускать.
Новых tasks/issues или слоя абстракции не требуется; три текущих reviewthreads
разрешаются только после тестов и независимого итогового ревью.
