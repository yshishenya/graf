# F227: анализ применимости и происхождения выпуска

Дата: 2026-10-17 Europe/Istanbul. Анализ проведён read-only после обновления
планирования; этот файл сохраняет его результат отдельным шагом. Исходный master:
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`. Lane: Active Spec Kit slice.

## Findings

| Уровень | Остаток | Решение |
|---|---|---|
| CRITICAL | 0 | Конституция не меняется; выпуск не выполняется. |
| HIGH | 0 | Прежний конфликт обязательной очереди с serial режимом устранён явным разделением действующего и будущего этапов. Это не завершает native очередь. |
| MEDIUM | 1 | Исторические T001–T031 все ещё unchecked при 27 закрытых child issues. Полная reconciliation остаётся в T030/#6237; новые T032–T033 не меняют их статус. |
| LOW | 0 | Матрица Python найдена в pinned source/run, дублировать её не требуется. |

Отдельный воспроизведённый дефект реализации base→source покрыт T033/FR-011/SC-007.
Наличие запланированного дефекта до implementation не является противоречием
требований и плана. До кода нужны независимый checklist gate и issue ownership.

## Покрытие требований

| Требования | Задачи | Приёмка |
|---|---|---|
| FR-001, FR-002 | T004, T007–T009, T011 | exact event/head/base и fail-closed |
| FR-003 | T010, T011, T029, T031 | authoritative mapping; реальный native этап открыт |
| FR-004 | T012, T015 | concurrency/cancellation |
| FR-005 | T013, T015 | final tracked/untracked cleanliness |
| FR-006 | T005, T014, T016 | metadata-only terminal receipt |
| FR-007 | T006, T017–T020 | immutable train/source/proofs |
| FR-008 | T018–T020 | stale/duplicate Full CI rejection |
| FR-009 | T029, T031, T032 | текущие serial checks; будущая очередь отдельно |
| FR-010 | T021, T022, T032 | pinned portable boundary/matrix |
| FR-011 | T033 | base ancestor actual source; три local commit objects |
| SC-001 | T007, T011, T028, T029 | matching target SHA |
| SC-002 | T012, T015, T020 | non-success rejection |
| SC-003 | T013, T015 | injected tree drift |
| SC-004 | T017, T020, T033 | три PR, один frozen candidate; serial fixture |
| SC-005 | T018–T020 | immutable decision/provenance |
| SC-006 | T021, T022, T032 | pinned Python 3.9/3.12 |
| SC-007 | T033 | serial PASS и orphan-base rejection без записи |

Покрытие: 18/18 (11 FR + 7 SC), 33 уникальных задачи, orphan tasks 0.
Покрытие задачами не означает выполнение. Итоговый T026/#6233 пока не закрывается:
этот срез лишь устраняет найденное противоречие, а общая F227 ещё не принята.

## Границы и последующие gates

- Обычный serial operator уже прошёл изолированный baseline; nullable SHA и
  новый режим не нужны. Caller release.sh создаёт настоящий synthetic commit.
- Предок synthetic без предка source ошибочно принят на исходном master.
  Исправление общее, schema/CLI не меняются. PR proofs в тесте подставлены.
- Native T029/T031 не подменяются unit tests. Никаких изменений queue/protection,
  нового Full CI, выпуска, приложения или production данных.
- После кода: focused tests, project validators, независимое ревью diff;
  отдельное разрешение на commit и draft PR, затем exact-SHA GitHub checks.
- Исходные закрытые issues не дублируются; scoped T032–T033 получают один owner.

## Входные контрольные суммы до реализации

- `spec.md`: `196f4b6f02f0feca8446ba766c9e6c77c4ed200ba2e3b4930ba315afb82df071`
- `plan.md`: `af3f86d6ff24e1828aca10d30f4df0a953b89d6c7e855b9426190deaa1179d60`
- `tasks.md`: `fafccceb25597202894283bfb5cbffbe5de356fdb01fcef6a8fcc77145bbd857`

Повторная read-only сверка после добавления ссылки ownership: T032–T033 принадлежат #7645; требования/план не изменились, CRITICAL0/HIGH0. Issue canon validate PASS (300 открытых Spec Kit issues).
