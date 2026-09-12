# Независимая проверка узкого исправления стенда

Дата: 2026-09-12. Reviewer: `capture_paths`.

## Требования до переноса

**PASS качества требований.** Прочитаны дополнения spec/plan/T007 и
checklists/infra.md; исходный diff e964bba55 проверен только для
scripts/dev-harness.py, tests/governance/test_graf_local_adapter.py,
infra/dev/README.md. CHK009–CHK011 отмечены reviewer.

Область определена двумя существующими MinIO service references
rec-minio/rec-minio-init. Только для них pull использует policy missing;
Temporal/Postgres сохраняют прежнюю загрузку. Отсутствующий образ требует
успешного pull, ошибка прекращает build до архива и подписи приложения.
Сохраняются существующие теги, image ID, exact SHA, архивы, подпись,
общая блокировка, rollback и production. T007 выполняется до T006;
предусмотрены focused pytest, независимый code review и новый exact-SHA CI.
Противоречий применимым требованиям constitution не найдено.

## Проверка перенесённого кода

**Approved: замечаний к переносу не найдено.**

Проверка `git diff e964bba55 -- scripts/dev-harness.py
tests/governance/test_graf_local_adapter.py infra/dev/README.md` дала пустой
diff: текущие байты всех трёх файлов совпадают с исходником. Изменение
относительно HEAD: 43 добавления, одно удаление, только эти три файла.
`git diff --check` прошёл.

Прочитаны GrafLocalAdapter.build, _run_command и проверки:

- MinIO pull выделен в отдельный вызов с policy missing; загрузка
  Temporal/Postgres не меняет параметры.
- Неуспешная команда выбрасывает HarnessError; build её не подавляет.
  Она выполняется до измерения/архивирования образов и сборки приложения.
- Измерение всех image ID, immutable tag, сохранение runtime-images.tar,
  exact-source проверки и проверка подписи остаются прежними.
- Параметризованная проверка отдельно моделирует недоступность каждого
  MinIO service и подтверждает отсутствие архива, app build и artifacts.

Прочитан предоставленный основным агентом результат focused pytest:
`43 passed in 0.48s` из `/tmp/graf-6796-harness-tests.log`. Независимая
попытка через системный python3 встретила отсутствие pytest; повторная
установка зависимостей не выполнялась. Таким образом, код и байты
проверены reviewer независимо, запуск тестов выполнен основным агентом.

Одобрение переноса не подтверждает установленный GRAF Dev, CI нового SHA
или выпуск. Следующие ворота — разрешённый коммит, build/promote штатного
стенда и exact-SHA CI.
