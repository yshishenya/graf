# Данные B019

Новых моделей нет. feature-claims.json: ID → {issue_number, branch, slug}; .specify/feature.json: действующий указатель. Online suggestion ничего не записывает. Allocation: clean tree → lock → live collisions → label/umbrella → shared claim → pointer. Ошибка останавливает создание; orphan label при внешней ошибке не означает reservation.

Метаданные миграции2026-09-09: `.specify/feature-numbering.json` содержит ровно
`out_of_sequence_spec_ids` без повторения ключа, список уникальных положительных целых ID без bool.
Нет счётчика/состояния выполнения. Отсутствие файла = пустой список исключений;
нечитаемый/невалидный файл = ошибка. Исключённый ID всё ещё занят.
