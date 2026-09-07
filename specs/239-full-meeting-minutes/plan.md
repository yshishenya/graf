# Implementation Plan: Полноценные итоги одним вызовом

**Branch**: `codex/239-simple-meeting-minutes` | **Date**: 2026-09-08
**Spec**: [spec.md](spec.md)

## Summary

Чистая реализация F239 от `7ff2c5c77ec007aac09cd86cded0579cd1a0443c`.
Старая ветка и PR #6787 — история, не источник готовых проверок.
Полная расшифровка → существующая фоновая задача → один вызов LLM →
техническая проверка → сохранение → существующие интерфейс и экспорт.

## Technical Context

- Language/Version: Python из действующего `apps/server/pyproject.toml`.
- Dependencies: существующие FastAPI, Pydantic, SQLAlchemy, Temporal, Langfuse,
  Jinja, openpyxl; без новых библиотек/сервисов.
- Storage: существующие PostgreSQL attempt/call/outcome/slot; одно nullable
  поле `MeetingOutcomeSet.protocol_json`. Миграция после текущего Alembic head,
  без переноса старых конфликтующих 0086/0087.
  Поля проекции owner/due расширяются до Text: модельный текст не обрезается,
  а существующие строки сохраняются без преобразований.
- Testing: pytest, существующий PostgreSQL runner, GRAF HTTP/Temporal и UI,
  затем GitHub Actions.
- Risk / Validation Lane: **high-risk-feature** — AI, приватные данные,
  хранение, интерфейс и публичные контракты.
- Release Gate: **no deploy**. PR требует `governance-fast` на точном SHA;
  отдельный релизный оператор выполняет Full CI, слияние и production.
- Performance: один логический этап LLM; повторный просмотр — ноль вызовов.
  Записать фактическое время прогона, не вводить обещания задержки без замера.
- Scope: сервер и серверный интерфейс, существующие macOS/WebView потребители.

## Constitution Check

До исследования: поправка §III 7.0.0 разрешает выбранную схему;
product-gates/PRD синхронизированы. Доступ, удаление, egress, durable ledger
и прежняя retry policy обязательны. После проектирования: протокол хранится
в той же удаляемой сущности, журнал остаётся retained; интерфейс не читает
приватный журнал для отображения. Production-метка не меняется.
Нарушений дизайна нет; реализация ждёт reviewer checklist и issue sync.

## Project Structure

- `outcomes/models.py`, `outcomes/prompts.py`: полный документ, схема,
  проверка ссылок; без extraction/verification моделей.
- `outcomes/ai_service.py`: существующий жизненный цикл, новый prompt
  resolution, validate/project и сохранение документа. Ответ сохраняется
  также при expiry/cancel/deletion/source race.
- `outcomes/generator.py` (`LiteLLMGateway`): убрать route-binding зависимости;
  обычная авторизация, ошибки и повторные попытки неизменны.
- `cli/langfuse_prompts.py`: исходный текст + небольшой адаптер JSON/refs;
  обновление текста не перезаписывает операторскую модель и параметры.
- `db/models/outcomes.py`, `db/migrations/versions/`: одно поле документа.
- `cabinet/`: общий вывод, таймкоды, таблица задач и сохранённые экспорты.
  Плоские API-поля — точная проекция документа, не второй генератор.
- `tests/`: компактные проверки контракта, жизненного цикла и отображения.

## Validation Plan

См. [quickstart.md](quickstart.md). Старые результаты не засчитываются.
Не запускать полный локальный CI. Содержательная оценка выполняется до PR
по настоящему выходу GRAF, без модельного оценщика в production.

## Complexity Tracking

Нет нового workflow, очереди, registry моделей, сервиса качества, таблицы
разрешений или promotion events. Чтение старых результатов — обязательная
граница истории, но новый запрос не использует старый генератор как fallback.
