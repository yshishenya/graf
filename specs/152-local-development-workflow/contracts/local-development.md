# Local Contract

`infra/scripts/start-local.sh` → `http://127.0.0.1:8081/login`; email
`local@graf.test`; code is visible only in development. The local flag selects
`graf_dev_owner_session` over HTTP. `apps/macos/Scripts/run-local-app.sh` sets both
cabinet and upload origins and accepts only loopback HTTP origins.
