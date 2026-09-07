# Validation
Использовать синтетические аккаунты/названия, не сохранять production cookie или частный контент.
1. Server: `cd apps/server && uv run pytest tests/unit/test_settings_view_models.py tests/unit/test_workspace_onboarding.py -q` и новые focused session unit checks.
2. Contract/integration через существующий `scripts/run_local_postgres_tests.sh --focused` (точные аргументы прочитать в --help): auth contracts, account routes, web owner session context, account lifecycle, RLS stale-session/device контекст. Изолированная БД обязательна.
3. Swift: существующая SwiftPM команда для DesktopCabinetWorkspaceTests и WebKit runtime regression. Проверить реальные form POST/redirect с GRAFDesktop UA на loopback origin; проверка initial header недостаточна.
4. Browser: синтетический account, app+browser+old+expired+revoked rows, текущий first; 375/768/1280 px; keyboard focus/details; no-JS confirm/cancel; CSRF denial; single/bulk success и отказ. Временная недоступность не показывает false success.
5. Security: device revoke invalidates principal-only auth/me и tenant APIs, legacy binding-only, чужой владелец, повтор, текущий protected. Billing handoff token отличен от source, expiry capped, replay и revoked source отклонены. last_seen bounded/не оживляет revoked.
6. `python3 scripts/check_spec_kit_governance.py`; scoped lint; converge/Ponytail review. PR `governance-fast` на exact SHA обязателен, full CI только отдельно перед релизом.
Все выполненные команды/результаты и честные ограничения фиксировать в evidence/implementation.md.
