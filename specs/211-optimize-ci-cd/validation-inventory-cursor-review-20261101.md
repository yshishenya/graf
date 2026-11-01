# F211/T115 — независимое ревью требований целевого inventory cursor

Дата: 01.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/Users/yshishenya/.codex/worktrees/f211-inventory-pagination/crisp`.
Ветка/source из `.specify/feature.json`:
`codex/f211-inventory-pagination-20261101`,
`125b51042ff39a1a7b1d4d051ce2503ea8d1250c`.
Полоса: active Spec Kit slice, только тестовая предпосылка T115.

**Requirements PASS; checklist3 отмечены/0 открыты; P1/P2/HIGH — 0/0/0.**

## Матрица

1. CHK001: новые sections spec/plan/tasks/quickstart прочитаны полностью.
   Настоящий Full41273275580 остаётся failure, а остальные8server shards/
   static/macOS PASS не превращают его в общий успех. Исторические workspace
   модульной БД объясняют неверное предположение first-page50. Меняется
   один курсор положительного inventory вызова. Все assertions точного
   TenantScope, inventory complete и отказа неверного maintenance context,
   page_size50, SQL, роли и RLS сохраняются. Рабочий цикл пагинации не меняется.
2. CHK002: один и тот же временный wrapper импортирует исходный test и две
   его fixtures, создаёт через существующий seed51 меньший workspace в
   настоящем disposable PostgreSQL и воспроизводит отсутствие цели на
   странице50. Исправленный test должен пройти на том же наборе. Штатный
   runner/cleanup и отсутствие новых skips обязательны; увеличение limit,
   очистка общей БД, retry до случайного успеха и ослабление matching assert
   прямо запрещены. RED должен дойти до исходного matching0 assertion,
   а не упасть на ошибке подготовки. Wrapper — диагностика, не новый API.
3. CHK003: None-path остаётся в двух вызовах другого maintenance test,
   включая позитивный inventory и отказ page_size51. В изменяемом test
   отрицательный неверный-context вызов с None тоже остаётся. Требуются
   весь normalization PostgreSQL module и весь maintenance-context file,
   focused/static/process/fragment/governance, независимое code review/
   converge и exact PR gates. Full/CD/T0 и коммерческий результат отдельно.

## Математическая корректность и фактические callers

PostgreSQL функция `rec_playback_normalization_workspace_page` использует
строгое условие workspace.id>cursor и order by workspace.id, limit≤50.
UUID сравниваются как128битное значение в порядке байтов; этот порядок
совпадает с unsigned UUID.int. Для цели T курсор T−1 делает T минимальным
возможным UUID строго больше курсора: между соседними целыми нет другого
UUID. Цель с seed meeting поэтому попадает первой, независимо от числа
старых workspace. Уникальный workspace key и прежний lateral limit1
исключают дубликаты целевого TenantScope в странице.

_seed_revision создаёт target через uuid4; его version bits исключают ноль,
так что вычитание1 не выходит за диапазон. UUID(int=...) не требует той же
версии/variant, что цель; SQL принимает корректный UUID курсора. Сам UUID
класс уже импортирован, нового helper/import/dependency не требуется.

Все найденные callers enumerate_backfill_workspace_candidates прочитаны:
один production `_inventory_legacy_workspaces` с cursor=None и последующим
last-row cursor, два вызова изменяемого postgres test и два вызова отдельного
maintenance test. Производственный цикл сохраняет проход следующих страниц
и завершение при len(page)<page_size. Других callers этого symbol в server
нет. Текущий SQL body, Python PostgreSQL/non-PostgreSQL ветви и role/context
admission прочитаны; их изменение в T115 не разрешено.

Для детерминированного wrapper важно сохранить и уникальность учебных slug:
_seed_revision использует uuid4().hex[:12]. Голые UUID(int=1), UUID(int=2)…
имеют одинаковый такой prefix и дадут ошибку подготовки вместо нужного RED.
Допустимая последовательность должна менять старшие биты/префикс, например
уникальные ограниченные ordinal<<80, либо сохранять отдельные уникальные
suffix values. Это техническое условие уже следует из требования выполнить
тот же seed и дойти до matching assertion; не новая продуктовая работа.
51 реально пригодный predecessor с seed meeting гарантирует, что первая
страница50 не содержит цель, а predecessor-cursor версия её содержит.

## Зависимости и ограничения чтения

Прочитаны root AGENTS и guidance index, текущие feature metadata, применимые
FR057/SC025, новые целые T115 sections, checklist, действующие test/seed/
fixtures и весь maintenance-context file, SQL function и рабочий pagination
consumer. Constitution VI requirements-review gate перечитан, baseline
constitution/PRD/status/product-gates/Spec Kit flow/release/process hashes
совпали с прежним собственным чтением, использовано ранее разрешённое F211
повторное чтение. Product/runtime/security behavior не меняется.

Full status взят из требований исполнителя, GitHub reviewer не открывал;
GREEN ещё не запускался и этим report не принят. RED независимо прочитан
по фактическому wrapper и журналу, как уточнено ниже. Перед
кодом сохраняются analyze и issue sync, затем тестовое доказательство и
независимое after-code review/converge. Failed release clone не меняется.

Изменены только назначенный checklist и этот report. Код/тесты/spec/plan/
tasks/Git/GitHub/CI/данные/серверы не менялись; тесты, сеть и контейнеры не
запускались. Чужие изменения сохранены. Checklist фактически перечитан после
записи: **3 отмечены/0 открыты**. Реализация, exact PR/новый Full/CD/T0
и коммерческая приёмка остаются отдельными.

## Хеши состояния до кода

- `specs/211-optimize-ci-cd/spec.md`: `4415a4065dac9c441fa8c46a6e15e161542877cd6bef2541e92f8b95f34906a8`.
- `specs/211-optimize-ci-cd/plan.md`: `6765a2b36fa03f71624c68aeeae2d072dbf9c404c08628a7a9af346813dd9a8c`.
- `specs/211-optimize-ci-cd/tasks.md`: `24a1805523f48d41c4ca4334fb5dcb86961d6674e3232f3fa6839b9fe464023e`.
- `specs/211-optimize-ci-cd/quickstart.md`: `726e865ed2aaf3cbc31b93ffc7c0b6a4e758adbcbbd1575835b19c9db1955abb`.
- `apps/server/tests/integration/test_playback_normalization_postgres.py`: `bf088c344d72690eeaccf900297f5a5f9a214758209cd94936ca5a3eff0ab94f`.
- `apps/server/tests/integration/test_rls_maintenance_context.py`: `7e18df137943011d766822b4d10782a6eb1ace96aa4b23b26abfbe04734c4c79`.
- `apps/server/src/twobrain_rec_server/normalization/pickup.py`: `78307541e6d2df34f2bebb1c277230a8ca97f0f3179adfc2817f40c59660d3b1`.
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py`: `59ad36f1c0720032f09d31d2a7abd0787e7a0ab49d889dd005c0a0c4460911d2`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.

## Дополнительное фактическое RED до реализации

Получены и самостоятельно прочитаны временный test_inventory_population.py
и inventory-reproduction-20261101.log. Wrapper импортирует неизменный test,
его migrated/media fixtures, задаёт module uuid4 последовательностью
UUID(int=value<<96) для1..9999 и создаёт51 predecessor через настоящий
_seed_revision. Такой шаг меняет первые12hex slug и сохраняет уникальность
всех generated ID; ранее описанный риск низких одинаковых prefixes здесь
отсутствует. Target, создаваемый тестом после fixture, строго больше всех51
предшественников. Monkeypatch восстанавливается после fixture, engine
закрывается в finally; весь disposable runner удалён.

Журнал подтверждает ровно ожидаемый matching0 вместо1, **1failed/3.82s**,
runner status fail и `postgres_test_cleanup=isolated_container_removed`.
Это содержательное RED исходного assertion, не setup failure либо случайный
UUID исход. Сам reviewer тест не запускал. Requirements PASS3/0 сохраняется;
код/test ещё не менялись, GREEN/implementation review остаются впереди.

- `test_inventory_population.py` SHA256: `a73d3176beba977b2041af3ffca4880b552393af1cf0284aa274389aae0d0911`.
- `inventory-reproduction-20261101.log` SHA256: `6880da537db56d69a7e2277e45ceba315e262c2cd32f6ae18a88b40ad8e87ff9`.
