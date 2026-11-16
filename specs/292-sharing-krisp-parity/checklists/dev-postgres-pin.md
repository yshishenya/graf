# Требования T041: воспроизводимый PostgreSQL Dev

Проверяет независимый reviewer до кода; состояние пунктов принадлежит reviewer.

- [x] DPP001 Область, цель и совместимость определены: закрепляется принятый PostgreSQL только в двух настройках Dev, без миграции, новых опций, изменения прав или внешних направлений. [spec: Session T041; plan: T041]
- [x] DPP002 Источник образа проверяем: официальный многоархитектурный OCI index, Linux arm64/amd64, соответствие принятому image ID; глобальные теги и manifests не редактируются. [plan: T041; quickstart: T041]
- [x] DPP003 Приёмка измерима и не подменяет guards: RED immutable/default equality, GREEN adapter/compose/schema-transition, прежний ранний отказ при разных образах, exact-SHA PR и отдельные штатные build/promote/status/smoke после интеграции. [tasks: T041; quickstart: T041]
