# Local development contract — superseded launch path

Запуск старого отдельного приложения заменён единым GRAF Dev.
Используйте [действующую инструкцию](/docs/agent-guidance/local-development.md):
`build → promote → status → smoke` через `infra/scripts/dev-harness.sh`.
Установленное приложение: `/Applications/GRAF Dev.app`, bundle ID
`pro.2brain.graf.dev`; cabinet/upload используют только loopback HTTP.
Dev-вход сохраняет `local@graf.test` и cookie `graf_dev_owner_session`.
