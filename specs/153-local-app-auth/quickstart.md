# Quickstart

```sh
infra/scripts/start-local.sh
apps/macos/Scripts/build-local-app.sh --open
```

In `GRAF Local`, use the local «Войти в кабинет» action, enter
`local@graf.test`, enter the code shown by the local server, and confirm that the
meetings view loads. A browser login is not reused by the app.

Validation: focused Swift cabinet tests, local `.app` build/launch, and
`infra/scripts/ci-local.sh --fast`; production deploy is out of scope.
