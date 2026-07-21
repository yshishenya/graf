# Quickstart: проверка feature 114

Все команды выполняются из корня checkout
`/private/tmp/crisp-114-support-incident-diagnostics`.

## 1. Проверить Spec Kit paths

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Ожидается `FEATURE_DIR=specs/114-support-incident-diagnostics` и v2 spec/plan
paths.

## 2. macOS report/truth tests

```sh
swift test --package-path apps/macos --filter DesktopUploadCustodyProjectionTests
swift test --package-path apps/macos --filter DesktopUploadClientTests
swift test --package-path apps/macos --filter DesktopUploadQueueTests
```

Ожидаемые сценарии: v2 JSON содержит stage/problem/correlations/timeline;
server deletion не объявляется delivered; raw failure/path не попадает в JSON;
clipboard использует тот же bounded report; sync-state безопасные поля
сохраняются.

## 3. Server privacy and Issue tests

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_support_incident_redaction.py \
  tests/unit/test_support_incident_github_issue_body.py \
  tests/contract/test_support_incident_contract.py \
  tests/integration/test_support_incidents.py
cd ../..
```

Ожидаемые сценарии: v1 и v2 принимаются; опасные поля отклоняются/редактируются;
Issue имеет `[114] ... T000`, feature/stage/problem labels и state matrix;
повторная доставка обновляет один Issue.

## 4. Negative metadata scan

```sh
rg -n --glob '*.swift' --glob '*.py' \
  '(/Users/|/private/|Bearer |token=|signed_url|transcript text|meeting content)' \
  apps/macos/Shared/Tests apps/server/tests
```

Совпадения допустимы только внутри negative-test fixtures/assertions; они не
должны появляться в generated report/Issue body.

## 5. Repository gate

```sh
infra/scripts/ci-local.sh
```

До запуска убедиться, что Docker/локальные зависимости доступны. Результат
`ci_local_result=pass` обязателен перед PR; production CD и release остаются
вне этого quickstart.
