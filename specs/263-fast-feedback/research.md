# Исследование F263, 2026-10-16

## Резерв и утраченные материалы

Существующий shared claim263 указывает на branch263-fast-feedback/#6901.
Повторный штатный claim прошёл на masteraaa5e7a2b01205d4ab962c7fb126ef7e99dadf7d.
Spec/plan/tasks/quickstart исходной F263 не найдены предыдущим исчерпывающим
Git-поиском; оригинальные четыре node IDs неизвестны. Сохранённые семь issues
позволяют восстановить критерии, но не выдумывать старые результаты.

## Принятые улучшения F211

tasks T055 и quickstart A5 описывают create_ready_meeting в speaker_names и
artifact_egress_policy: исторический27-case125.71→66.95s, один before/after.
A10:131cases342.418→194.739s сworkers4. Это не три повтора четырёх исходных
тестов F263 и неworkers1/2; T002/T005/T008 не принимаются автоматически.

## Решение по US4

Карта scripts/ci-behavior-tests.py содержит только cabinet-shell/settings.
performance_path в ci-local уже выбирает calendar integration, но не оба
contract/integration через общую карту. Существующий PostgreSQL runner в
--focused без --partitioned выполняет одну реальную pytest выборку и убирает
контейнер; JUnit подходит прежнему check_execution. Это минимальное повторное
использование. Отдельный executor/контейнер/зависимость не нужны.

Изменять только карту недостаточно: cabinet shared начнёт выбирать все группы,
старый execute запустит integration без изолированной БД, fast повторит performance.
План охватывает все три общие точки и существующих вызывающих.
