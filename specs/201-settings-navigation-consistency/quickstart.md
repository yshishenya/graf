# Quickstart: Единая точка входа в настройки

## Focused checks

```sh
cd apps/server
uv run pytest tests/unit/test_cabinet_template_sections.py tests/contract/test_settings_ui_contract.py tests/integration/test_settings_ia_flow.py -q
```

## Manual scenarios

1. Открыть `/meetings` в browser, раскрыть меню профиля: видны имя/email, «Настройки» и «Выйти», а «Закрыть GRAF» отсутствует.
2. Перейти в `/settings`: основной sidebar сохраняет канонический «Настройки» и категории; профильное меню сохраняет surface-aware вход в настройки аккаунта и корень настроек.
3. Повторить 1–2 во встроенном `/desktop/meetings` и `/desktop/settings`.
4. Проверить compact rail и клавишу Escape: меню закрывается, фокус возвращается на trigger.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

Для текущего release closeout deploy выполняется отдельно на точном post-merge SHA с явно одобренным пропуском полного CI; notarization для локального DEV-артефакта не является production-доказательством.
