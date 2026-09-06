# Технический срез T058: локальная проверка

Дата: 2026-09-06. Lane: `high-risk-product`, действующая Feature 239.
Ветка: `codex/239-model-config-unlock`.
База: `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`.
Implementation commit и PR ещё не созданы; это не exact-SHA CI receipt.

## Проверенная граница

FR-036/037 реализованы для действующего плоского outcome contract:
config 5, технический root v2/export v2, модельные настройки из exact Langfuse
versions, без дополнительного ограничения одной моделью. Текст действующих
промптов, схема результата и renderer не заменялись новыми протоколами.
Разница runtime/infra: 214 добавленных, 476 удалённых строк; новых зависимостей нет.

Независимый просмотр `prompts.py`, `prompt_bundle.py`, `cli/langfuse_prompts.py`
и их тестов не выявил новых P1/P2. Основной агент проверил gateway, сохранение
и публикацию calls, наблюдаемость и optimizer. Найденные silent overwrite
generator hash и потеря сообщённой модели у ошибочного ответа исправлены
с отрицательными регрессиями. Повторный просмотр этих исправлений завершён.

Сверка технического кода с FR-036/037 и границей T058 не выявила нового
неучтённого объёма реализации. Это не convergence всей Feature 239:
её новый протокол, качество корпуса и релизные задачи остаются открытыми.
Reviewer-owned отметки требований не изменялись.

## Проверки

Команды двух pytest-наборов приведены в
[процедуре T058](../model-settings-release.md#проверки-до-pr).

| Проверка | Результат |
| --- | --- |
| Unit/contract: prompts, root/export, optimizer, gateway, Langfuse | 129 passed |
| Расширенный PostgreSQL-набор: revisions, publication, dispatch, workflow, deletion | 105 passed |
| `uv run --extra dev --extra evaluation ruff check .` в apps/server | PASS |
| `python3 scripts/check_spec_kit_governance.py` | PASS |
| `python3 scripts/check-development-process.py` | PASS |
| `git diff --check` | PASS |
| Поиск удалённого descriptor/callback/headers/allowlist в src/tests/infra | Совпадений нет |
| Проверка распространённых форматов ключей и подписанных URL в затронутых исходниках и новых материалах | Совпадений нет |

Всего 234 теста; каждый набор сообщил два прежних предупреждения pytest/Starlette.
В промежуточном PG-прогоне три старые тестовые заготовки не содержали полного
закрепления model/settings/hash. Обновлена только подготовка синтетических
данных; runtime-проверка не ослаблялась. Весь расширенный набор затем пройден
повторно. PostgreSQL использовал отдельный временный контейнер, удалённый
runner после проверки; production database не использовалась.

Локально проверен настоящий Langfuse SDK 4.15.1: `LangfuseGeneration` → OTel
→ OTLP serialization/decode сохраняет полную вложенную схему параметров.
При `model=None` модель не подставляется из requested alias. Сетевой клиент
не создавался; приём данных живым Langfuse этой проверкой не подтверждён.

Ponytail review: отдельные сервисы, зависимости, fallback или новая model
allowlist не добавлены; общая проекция параметров переиспользуется. Удаление
не ослабляет source/deletion fences, HTTP/JSON/schema и retained hash checks.
Частное содержимое встреч не использовалось в новых fixtures или evidence.

## Идентичность проверенного кода

SHA-256 `git diff --binary -- apps/server infra/litellm`:
`c54b8e9e99c5e932c11be4230eaeaec341920dd763761e9f53e95e0c99fc6ed8`.

Отдельно SHA-256 нового `apps/server/tests/fixtures/outcome_prompts.py`:
`44902288ab997280628069f4c6358998aa13c9232b0801e0a69255cc99c5d80f`.
После коммита PR обязан ссылаться на фактический SHA, а required CI — пройти
именно для него; эти локальные хеши не заменяют GitHub evidence.

## Операционная проверка и оставшиеся этапы

Read-only metadata LiteLLM: ключ ГРАФ имеет `all-team-models`, его команда —
`all-proxy-models`. Второго ограничения одной моделью в этих списках нет.
Специальный callback в production пока не удалялся. Ключи, обычная авторизация,
бюджеты и провайдерские маршруты не менялись.

Не выполнены: implementation commit/push/PR, exact-SHA `governance-fast`,
release-full, CD dry-run/deploy, продвижение Langfuse root/LKG, согласованное
удаление production callback, synthetic smoke нескольких моделей и живой
проверенный экспорт наблюдений. Они принадлежат T058 и не считаются PASS.
Основной корпус и качество новых протоколов принадлежат T043–T048/T059;
этот технический отчёт их не принимает и не закрывает.
