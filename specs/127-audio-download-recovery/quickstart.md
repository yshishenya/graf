# Quickstart: Восстановление скачивания аудио

## Быстрая проверка

Из корня репозитория:

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
(cd apps/server && uv run --extra dev pytest -q \
  tests/contract/test_recording_governance_ui_contract.py \
  tests/contract/test_cabinet_static_assets_contract.py)
```

Для macOS shell:

```sh
cd apps/macos
swift test --filter DesktopCabinetConfigurationTests
swift test --filter DesktopCabinetRoutePolicyTests
```

## Acceptance scenarios

1. Synthetic allowed meeting: открыть `Ещё` → `Скачать аудио…`; default navigation/download должен начаться, а меню закрыться сразу после dispatch.
2. Synthetic denied/unavailable meeting: menu item не рендерится либо existing server policy отклоняет запрос; private detail не заменяется download response.
3. Отменить системное сохранение и повторить действие; повторный request должен быть возможен.
4. Проверить, что test output содержит только metadata/status и не содержит audio, transcript, storage URL или credentials.

## Repository gate

После focused checks запустить из корня:

```sh
infra/scripts/ci-local.sh
```

Local PostgreSQL integration tests запускать через предусмотренный проектом runner, если его зависимости доступны; отсутствие `TWOBRAIN_DATABASE_URL` само по себе не является основанием менять egress contract.

## Validation evidence

Дата: 2026-07-25. Все результаты metadata-only; meeting content и audio bytes в evidence не записывались.

- PASS — `node --check` для cabinet JS.
- PASS — focused server contract suite: 43 passed.
- PASS — artifact/detail PostgreSQL suite: 37 passed; isolated test container удалён.
- PASS — macOS focused tests: `DesktopCabinetConfigurationTests` 25 passed и `DesktopCabinetRoutePolicyTests` 14 passed.
- PASS — `infra/scripts/ci-local.sh`: macOS 637 tests, server 2420 parallel + 41 strict (1 skipped), lint, compile, compose и deployment evidence scan.
- Expected scope note — CI сообщил `rls_validation_result=blocked` для production enforcement probe, потому что no-deploy lane не предоставляет production database; это не блокирует локальные tests и не меняет egress policy.
