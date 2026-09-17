# Quickstart — GRAF Dev

Старый путь запуска заменён единым [Dev-стендом](/docs/agent-guidance/local-development.md).
Проверьте текущий manifest командой `infra/scripts/dev-harness.sh status --json`,
затем выполните build/promote/smoke выбранного SHA по инструкции стенда.
Откройте `/Applications/GRAF Dev.app`; кабинет доступен на
`http://127.0.0.1:8081/login`, тестовый аккаунт `local@graf.test`.
Код входа берётся из текущей Dev-конфигурации.

Отдельный bundle и прямой запуск Swift больше не используются.
