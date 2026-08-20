# Quickstart: проверка подключения email без тупиков

## Focused automated checks

```sh
cd apps/server
uv run pytest \
  tests/unit/test_account_merge_policy.py \
  tests/unit/test_workspace_onboarding.py \
  tests/contract/test_account_merge_contract.py \
  tests/contract/test_account_routes.py \
  tests/contract/test_auth_contracts.py \
  tests/integration/test_account_merge.py
```

Проверить отдельно существующие email/Yandex/VK сценарии:

```sh
cd apps/server
uv run pytest \
  tests/contract/test_auth_contracts.py \
  tests/contract/test_provider_link_settings_contract.py \
  tests/integration/test_account_merge.py \
  -k 'email or yandex or vk or provider_link or account_merge'
```

Для trust boundary выполнить существующий disposable PostgreSQL/app-role probe,
указанный тестами account merge и RLS. Owner-role SQLite/HTTP check не заменяет
эту проверку.

## Manual web journey

1. На локальных synthetic данных создать два active профиля с отдельными
   personal workspaces и разными verified способами входа.
2. Из текущего профиля начать `Подключить email`, ввести тестовый код и открыть
   preview.
3. На wide и 390px viewport проверить IA, фактические provider labels, отсутствие
   overflow, keyboard focus, disclosure и console errors.
4. Сначала отменить и доказать zero mutation.
5. Создать новый intent, подтвердить и доказать: current personal workspace не
   изменился; source workspace стал `linked`; оба workspace/meeting IDs прежние;
   все sessions/devices revoked; login каждым сохранённым provider работает.
6. Проверить stale, replay, concurrent confirm и injected rollback.
7. Проверить missing/wrong browser nonce, revoked initiating session/source
   identity, expired confirm и completed replay с другим key.
8. Поочерёдно проверить billing, calendar, deletion, role и meeting blockers и
   перейти по каждому предложенному действию.

## Embedded macOS journey

1. Запустить локальный сервер и отдельную `GRAF Dev` сборку.
2. Повторить preview, cancel, blocker и confirm через `/desktop/...` routes.
3. Убедиться, что links не выходят из first-party allowlist, layout не
   перекрывается native chrome, provider start активирует external-auth
   continuation, а success ведёт на повторный вход.

## Closeout

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/cd-remote.sh --dry-run
```

Вторую команду выполнять перед production deploy. Полный CI не запускать на
каждой итерации; он остаётся release gate для точного candidate SHA.
