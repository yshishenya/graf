# Проверка

Из apps/server, Python 3.13+ с dev dependencies; PYTHONPATH=src, чтобы использовать текущий worktree.

```sh
PYTHONPATH=src uv run --extra dev pytest tests/unit/test_cabinet_web_shell.py tests/contract/test_recording_governance_ui_contract.py tests/contract/test_recording_workflow_accessibility.py tests/unit/test_deletion_report_view_models.py tests/contract/test_deletion_no_secret_leakage.py -q
# Из корня репозитория:
node apps/server/tests/browser/meeting-delete-focus.test.cjs
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
swift test --package-path apps/macos --filter 'DesktopCabinet(Route|NavigationRequest)PolicyTests'
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_cabinet_hx_delete_feedback.py tests/integration/test_cabinet_csrf.py -q
```

Второй набор запускает штатную изолированную тестовую PostgreSQL в Docker и удаляет её после проверки; skipped не считается PASS. Ruff проверяет три затронутых Python файла. Из корня git diff --check.

Ручная приёмка перед выпуском: только /Applications/GRAF Dev.app через dev-harness из чистого разрешённого SHA. Открыть синтетическую встречу, Ещё → Удалить: текст соответствует spec, две кнопки, без технического списка/ссылки. Проверить обе темы, узкую ширину, Tab/Shift-Tab, Escape, отмену, возврат фокуса. Для подтверждения использовать только синтетическую встречу. Сравнить web/embedded. Не считать синтетический HTML проверкой установленного приложения.

PR: governance-fast на точном SHA; выпуск: release-full, штатные release/deploy gates. Результаты и ограничения записывать в validation.md.
