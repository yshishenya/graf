# Quickstart: непрерывность способов входа при ошибках

## Preconditions

- Использовать только синтетические email и локальный тестовый PostgreSQL.
- Не отправлять реальные письма и не менять production accounts/configuration.
- Проверять browser и разрешённый embedded `/desktop/...` next path.

## Focused scenarios

1. Unknown/unselectable login email: HTTP 400, правдивый non-enumerating текст,
   нормализованный email, активные Яндекс ID/VK и отсутствие созданного кода или
   сессии.
2. Invalid email, invitation mismatch, rate limit и delivery failure:
   соответствующий status/header/error сохраняется; доступные провайдеры не
   исчезают; сырой неверный email не отражается.
3. Sign-up workspace unavailable, invalid email, rate limit и delivery failure:
   provider snapshot и нормализованный email следуют тому же контракту.
4. Provider-start future/missing/disabled/rate-limited: соседние разрешённые
   способы сохраняются, отключённый не появляется, state/nonce не создаётся на
   раннем отказе.
5. Policy с Yandex+VK, только Yandex, только VK и без обоих: error screen точно
   повторяет разрешённое состояние; planned entries не становятся активными.
6. Policy/DB/workspace unavailable: экран остаётся fail closed и не изображает
   Яндекс ID/VK доступными.
7. HTML-подобный и смешанный регистр/пробелы в email: только успешно
   нормализованное значение появляется в `value`, Jinja его экранирует.
8. Успешные email, invitation, Yandex ID, VK и ambiguous-account recovery tests
   остаются зелёными.

## Commands

```sh
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_web_owner_session_context.py \
  tests/contract/test_auth_contracts.py \
  tests/contract/test_account_routes.py \
  -k 'browser_email or browser_yandex or browser_vk or browser_telegram or browser_login_page or browser_signup_page or throttled_browser_provider_start or auth_email_input'

cd "$repo_root/apps/server"
uv run --extra dev ruff check \
  src/twobrain_rec_server/cabinet/web_routes/auth.py \
  src/twobrain_rec_server/cabinet/auth_rendering.py \
  tests/integration/test_web_owner_session_context.py \
  tests/contract/test_auth_contracts.py \
  tests/contract/test_account_routes.py

uv run python -m compileall -q \
  src/twobrain_rec_server/cabinet/web_routes/auth.py \
  src/twobrain_rec_server/cabinet/auth_rendering.py

cd "$repo_root"
git diff --check
infra/scripts/ci-local.sh --fast
```

После push обязательный `governance-fast` должен пройти на том же 40-символьном
SHA, который записан в PR. Deploy и полный release CI в эту задачу не входят.
