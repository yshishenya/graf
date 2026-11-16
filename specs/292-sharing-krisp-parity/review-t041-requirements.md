# Независимая проверка требований T041

Дата: 2026-11-17. Результат: PASS, C0 / H0 / M0. Это проверка требований до кода; не приёмка реализации или стенда.

| Пункт | Проверенные доказательства | Результат |
|---|---|---|
| DPP001 | T041 в spec.md задаёт цель воспроизводимой сборки, отсутствие миграции/новых опций и сохранение данных/прав. plan.md ограничивает исправление двумя исходными настройками и существующим тестовым модулем. Реальные `_env(pin_images=False)` и build inspect берут одно объявление `COMPOSE_IMAGE_COMPONENTS`; Compose имеет отдельный fallback, поэтому согласование двух строк покрывает оба пути. | Подтверждён |
| DPP002 | В read-only registry JSON подтверждён `application/vnd.oci.image.index.v1+json` и Linux amd64/arm64. Дочерний arm64 manifest имеет config `sha256:25a89970a83255ae96484d709005bb35aa71f7455f941bc1634514f31c5d5c62`; локальный `docker image inspect` официального `postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24` возвращает тот же ID, arm64/linux. Активный manifest `dev-c8de0b01ca5d` содержит тот же database digest. Запрет изменений manifests/данных/глобальных тегов явно записан в spec/plan/tasks. | Подтверждён |
| DPP003 | quickstart содержит предметный RED `-k postgres_default`, полный focused adapter/compose/schema-transition и названия обоих действующих тестов отказа. plan/tasks явно оставляют exact-SHA PR и последующие штатные build/promote/status/smoke владельцу стенда; требования не объявляют source-проверки живой приёмкой. `_assert_transition_compatible` сейчас действительно отклоняет отличающиеся persistent formats. | Подтверждён |

Прочитаны T041 и связанные FR-015/027 в spec.md, план, tasks.md, quickstart.md; AGENTS.md, Spec Kit risk/reviewer gates, constitution Development Workflow And Quality Gates, правила локального стенда; текущие объявления/потребители образа и существующие тесты отказа. Использованы только обезличенные registry/config/image identities и active database digest.

Повторно прочитан checklist: 3 подтверждённых / 0 неподтверждённых. Изменены только checklist и этот отчёт. Продуктовый код, spec/plan/tasks, Git/GitHub, данные, контейнеры, manifests, приложения и теги не менялись.

Не проверены будущие RED/GREEN, сборка/переход, PR checks и выпуск; они обязательны отдельно.
