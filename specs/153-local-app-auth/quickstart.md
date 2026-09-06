> Путь запуска обновлён: используйте единственный `/Applications/GRAF Dev.app` через `infra/scripts/dev-harness.sh`; см. [действующую инструкцию](/docs/agent-guidance/local-development.md). Старые отдельные приложения больше не собираются.

# Quickstart

```sh
infra/scripts/dev-harness.sh status --json
```

После build/promote/smoke по действующей инструкции, in `GRAF Dev`, use the local «Войти в кабинет» action, enter
`local@graf.test`, enter the code shown by the local server, and confirm that the
meetings view loads. A browser login is not reused by the app.

Validation: focused Swift cabinet tests, local `.app` build/launch, and
`infra/scripts/ci-local.sh --fast`; production deploy is out of scope.
