# Quickstart: проверка подключения email в macOS

## Focused automation

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetConfigurationTests
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetNavigationRequestPolicyTests
PYTHONPATH=apps/server/src uv run --project apps/server pytest -q apps/server/tests/contract/test_account_routes.py
PYTHONPATH=apps/server/src uv run --project apps/server pytest -q apps/server/tests/integration/test_web_owner_session_context.py -k authenticated_email_link_failure_is_audited_before_terminal_callback
infra/scripts/ci-local.sh --fast
```

## Metadata-safe app smoke

1. Открыть локальную подписанную GRAF Dev сборку и настройки аккаунта.
2. На синтетическом аккаунте отправить форму подключения email.
3. Убедиться, что экран кода остаётся видимым, resend/back остаются embedded,
   а общий экран ошибки встречи не появляется.
4. По metadata-only логам подтвердить один POST, отсутствие автоматического GET
   на start endpoint и отсутствие 405.
5. Проверить конечный redirect после синтетического кода либо mock/dev-code
   сценария: страница аккаунта должна появиться сразу, без пустого окна,
   повторного GET и ручного обновления.

Не записывать email, код, cookie, token, nonce, account id, встречу, transcript
или другие персональные данные.
