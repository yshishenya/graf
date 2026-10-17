# Implementation Plan: F263 / календарные проверки и повторное чтение

**Branch**: `263-fast-feedback` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Возобновить существующую F263 по #6901/#6904–#6909. Первая проверенная часть —
US4/T009; следующий самостоятельный этап US1/T003 описан в конце плана.
US2/US3 и итоговая приёмка всей фичи сохраняются открытыми.

## Technical Context

**Language/Version**: Python >=3.12 (сервер; локальное окружение 3.13), Bash 3.2+ (штатные скрипты).
**Primary Dependencies**: stdlib, существующие pytest/uv; новых зависимостей нет.
**Storage**: только временный изолированный PostgreSQL из штатного runner.
**Testing**: существующий test_ci_cd_contract.py и оба календарных файла.
**Risk / Validation Lane**: active-spec-slice с полными воротами significant-feature;
общий выбор и исполнение проверок затрагивает несколько модулей, использует Docker/Postgres.
**Release Gate**: без deploy; перед merge три обязательных exact-SHA PR checks;
перед отдельным выпуском frozen release-full и разрешение пользователя.
**Target Platform**: macOS/Linux, штатные локальные CI команды.
**Project Type**: внутренние скрипты проверки репозитория.
**Performance Goals**: не добавлять повторный запуск полного calendar integration;
существующий serial_performance порог обязателен, новых обещаний ускорения нет.
**Constraints**: общий Dev не менять; не копировать зависимости; малые проверки
используют уже установленное окружение и образ Postgres, при завершении cleanup.
**Scale/Scope**: одна дополнительная группа, три изменяемых файла кода/тестов.

## Constitution Check

До Phase0: PASS. Принципы I–V/VII не меняются; продукт, реальные пользовательские
данные, capture, UI и внешние сервисы не затрагиваются. VI: specify/clarify,
план, reviewer-owned checklist, задачи, analyze, issue sync до реализации.
После Phase1: PASS. Миграции и RLS выполняет существующий runner, изоляция не
ослабляется. Конституционных изменений и исключений нет.

## Phase0 / Research

См. [research.md](research.md). Решение — дополнить существующую карту;
не строить граф зависимостей или отдельный тестовый runner.

## Phase1 / Design

1. `scripts/ci-behavior-tests.py`: добавить calendar-auto-context для календарного
   каталога, API, модели, миграции0021 и самих mapped tests. Группы кабинета
   ограничить их областью: прежнее shared условие не должно выбрать новый календарь.
2. Список tests/covered_tests — объединение без повторов, прежняя проверка
   существования/AST/containment сохраняется для каждой выбранной цели.
3. При наличии calendar integration `execute` вызывает существующий
   `run_local_postgres_tests.sh --focused` без partitioned: одна последовательная
   pytest выборка, один JUnit, реальные миграции/RLS, required performance gate.
   PYTEST_ADDOPTS сбрасывается; addopts пуст; пропуски/деселекция файлов проверяются
   прежним check_execution. Без календаря прежний Python/Node путь сохраняется.
4. `infra/scripts/ci-local.sh`: полные behavior targets исключаются из changed_tests;
   наличие целого calendar integration в них покрывает отдельный performance этап.
   Остальные unit/component/static gates не отменяются.
5. JSON environment отражает PostgreSQL/Docker только для календарной выборки;
   coverage остаётся partial, changed_paths и diff_available сохраняются.

### Точное соответствие источников

Любой из следующих путей выбирает одну группу `calendar-auto-context`:

- `apps/server/src/twobrain_rec_server/calendar/` (включая `matching.py`);
- `apps/server/src/twobrain_rec_server/api/calendar.py`;
- `apps/server/src/twobrain_rec_server/db/models/calendar.py`;
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py`;
- сами `apps/server/tests/contract/test_calendar_auto_context_contract.py`
  и `apps/server/tests/integration/test_calendar_auto_context_match.py`.

Для каждого источника обе цели, относительно `apps/server/`:
`tests/contract/test_calendar_auto_context_contract.py` и
`tests/integration/test_calendar_auto_context_match.py`.
Удаление или переименование источника сохраняет выбор по прежнему пути;
переименование обязательного теста требует одновременного обновления карты.

## Validation Plan

Сначала воспроизвести отсутствие calendar selection направленным тестом. Затем:
matching/API/model/другой calendar module/миграция/сам mapped test; смешанная
выборка/covered; cabinet isolation; unknown/shared/rename/bad base;
missing/empty/syntax/symlink; execution skip/deselect/failure; реальная команда
runner и оба календарных файла с required performance. Полный существующий
CI contract файл, соседний runner contract и governance — регрессия.
Крупная сборка macOS не нужна для этих скриптов, installed/native приёмка не заявляется.

## Project Structure

- `scripts/ci-behavior-tests.py` — карта и существующий исполнитель.
- `infra/scripts/ci-local.sh` — существующая последовательность этапов.
- `apps/server/tests/contract/test_ci_cd_contract.py` — направленные проверки.
- `specs/263-fast-feedback/` — восстановление, текущие требования, review и evidence.
- `changes/unreleased/F263.yaml` — фактическая часть результата.

## Dependencies

T009 допускается после текущего полного ревью требований, analyze и сверки #6908.
Не зависит от утраченных четырёх node IDs: ни fixtures, ни чтение, ни разбиение
не меняются. T001/T002 и вся US1–US3 не принимаются этим разрешением на работу.
T010/T011 всей фичи остаются открытыми. Унаследованный блокер F259 проверяется
штатно, без отключений валидатора. Commit после проверки требует разрешения.

## Независимая US1 / #6905 — 2026-10-16

Lane: significant-feature / governance, документация без изменения обязательных
продуктовых проверок. Constitution check до исследования: PASS — первое полное
чтение, все ограничения и отдельное изменение принципов сохраняются.

Минимальное решение: одна процедура в
`docs/agent-guidance/document-reading.md` и ссылка из существующего README.
Новый загрузчик документов, автоматически выбранные отрывки, копии требований,
кэш между диалогами и изменения AGENTS.md не нужны. Использовать штатный
`shasum -a 256` для подтверждения неизменности каждого уже прочитанного файла.

До реализации: независимый `checklists/document-reading.md`, analyze и сверка
#6905/T003. Затем четыре документальных сценария на текущем содержимом:
известная область, пересечение, неизвестная область и изменение принципа.
Отдельные отказы: чтение только заголовков/поиска, изменённый хеш, недоступный
файл, новый диалог, чтение другим агентом, сомнение в полноте, новая зависимость.
Подсчёт фактических UTF-8 байтов не выдавать за измерение токенов или времени.
Результат и ограничения записать в validation.md; review и converge отдельно.

US1 не требует исходного benchmark US2 и не меняет US4. Перед изменениями
область владения расширяется только на два указанных файла документации.
После проверки — отдельное разрешение на новый коммит; действующее разрешение
F263 относилось к уже закоммиченной US4. PR остаётся черновиком.

Constitution check после Phase1 US1: PASS — процедура не меняет принципов или
обязательного первого полного чтения, проверяет доступность полного содержания
после сжатия истории и не разрешает заменять требования хешем/пересказом.
