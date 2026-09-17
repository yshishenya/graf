# Validation

## Prerequisites
Изолированная PostgreSQL из существующей pytest fixture; установленный uv и Swift. Ручные проверки только /Applications/GRAF Dev.app через dev-harness, после чистого разрешённого коммита; production не менять.

## Commands
- bash apps/server/scripts/run_local_postgres_tests.sh tests/unit/test_auth_session_renewal.py tests/unit/test_auth_session_clients.py tests/unit/test_config_validation.py tests/contract/test_auth_contracts.py tests/integration/test_rls_stale_session_device_context.py tests/integration/test_account_lifecycle.py::test_bulk_device_revoke_and_activity_use_same_lock_order
- cd apps/macos && swift test --filter 'DesktopCabinetSessionBridgeTests|DesktopUploadClientTests|DesktopUserTimeContextTests'
- python3 scripts/check_spec_kit_governance.py
- git diff --check

## Scenarios
Контролируемые часы: выдача 30 дней, активность перед сутками, после 30 дней от первого входа, ровно на границе, явный выход/отзыв/потеря membership, конкурентное продление, отказ commit, потерянный ответ, custom TTL. Cookie Secure/HttpOnly/SameSite и route override. Повторные registry 304 без навигации. Native same-origin/same-token обе копии, меньший срок, поздний ответ после logout/смены аккаунта, отсутствие auth-change при продлении. Сеть/сон не очищают cookie.

Ручная приемка после установки: вход, нативный запрос без навигации, новый срок обеих копий без раскрытия токена, перезапуск и открытие встречи, выход с ожидающим запросом. В evidence отделять unit/integration от установленного приложения; governance-fast/релиз остаются отдельными gates.

Дополнительная проверка роли БД: bash apps/server/scripts/run_local_postgres_tests.sh tests/integration/test_rls_postgres_policies.py::test_session_renewal_commits_under_exact_app_role_without_cross_tenant_access tests/unit/test_auth_session_renewal.py -q.

Для frozen governance использовать изолированную установку specify из точного ref .specify/speckit-bootstrap.lock.json, если глобальная версия отличается; не менять lock ради локальной проверки.
