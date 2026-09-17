# Проверка требований F256: infra

Reviewer-owned. Исполнитель не отмечает пункты. Первый этап без ножниц.

- [x] CHK001 Определены ли одна миграция, её head, RLS и сохранение старых прав? [data-model.md]
- [x] CHK002 Отсутствуют ли ненужные очереди/внешние сервисы/новые зависимости, и сохранены ли границы AI/захвата? [plan.md, Constitution I–III]
- [x] CHK003 Разделены ли scoped проверки, PostgreSQL, браузер, Dev, exact-SHA PR и выпуск? [quickstart.md, SC-006]
- [x] CHK004 Предусмотрены ли полная очистка новых сущностей и транзакционная согласованность уведомлений? [data-model.md]

Независимый reviewer `requirements_review`, 2026-09-08: требования проверены,
не реализация. Evidence: plan.md «Technical Context»/«Project Structure»;
data-model.md «Права и жизненный цикл»; quickstart.md. Миграция0090 следует
существующему merge head0089. Проверки выпуска не заменяются проверкой браузера.
Общий переход к реализации зависит также от [requirements-review.md](../requirements-review.md).
