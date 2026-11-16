# Проверки T041 — закрепление PostgreSQL Dev

## Область и статус

Active Spec Kit slice / high-risk-product. Локальная реализация готова; T041 и #8121 остаются открытыми до штатных build/promote/status/smoke интегрированного чистого SHA и точных GitHub ворот. Никаких live build/promote/runtime действий в этой проверке нет.

## Требования и источник

Независимый reviewer: `checklists/dev-postgres-pin.md` 3/3, `review-t041-requirements.md` C0/H0/M0. Анализ `analysis-t041.md`: C0/H0. Issue canon ensure выполнен, duplicate search T041 пуст до создания #8121; validator PASS, 280 issues.

Registry read-only: официальный postgres OCI index sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24, Linux amd64 и arm64/v8. Arm64 manifest sha256:0b2882c46a2b8d8e148431b333394348cf4d7f15aec6df7f17d51dc641e56cfa имеет config sha256:25a89970a83255ae96484d709005bb35aa71f7455f941bc1634514f31c5d5c62; локальный inspect возвращает тот же image ID, arm64/linux. Это accepted image, а не новое обновление PostgreSQL.

## RED → GREEN

- До изменения двух defaults: `python -m pytest -q tests/governance/test_graf_local_adapter.py -k postgres_default` — ожидаемый FAIL (1 failed, 60 deselected): mutable postgres:17-alpine не соответствует immutable registry reference.
- После: `python -m pytest -q tests/governance/test_graf_local_adapter.py tests/governance/test_dev_compose_contract.py tests/governance/test_dev_schema_transition.py` — PASS, 125 tests, 5.04s.
- Включены все варианты `test_transition_cannot_change_persistent_formats` и `test_stateful_image_change_refused_before_stop`; guard не изменён.
- `ruff check scripts/dev-harness.py tests/governance/test_graf_local_adapter.py` — PASS.
- `git diff --check` — PASS.

Использовано существующее Python-окружение соседней принятой рабочей копии; новых зависимостей не установлено. Тесты файловые/с подстановкой команд, приложение и Docker runtime не запускают.

## Converge

Проверены четыре требования T041, два объявления PostgreSQL, общий build/inspect/env путь и оба существующих refusal tests: дополнительной отсутствующей реализации не выявлено. Новая задача не добавлена. Полная F292 не объявляется завершённой: её native, PR, release/runtime и tracker gates ведёт root отдельно.
