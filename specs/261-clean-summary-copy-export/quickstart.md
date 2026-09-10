# Проверка F261

В корне репозитория:

```sh
cd apps/server
uv sync --frozen --extra dev
.venv/bin/python -m pytest tests/unit/test_content_export_request_runtime.py tests/unit/test_meeting_protocol_rendering.py tests/unit/test_transcript_exports.py tests/unit/test_meeting_source_viewport_runtime.py tests/unit/test_cabinet_web_shell.py::test_120_meeting_detail_renders_one_accessible_metadata_only_export_dialog -q
.venv/bin/ruff check src/twobrain_rec_server/cabinet/rendering.py tests/unit/test_content_export_request_runtime.py tests/unit/test_cabinet_web_shell.py
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd ../..
git diff --check
python3 scripts/validate-agent-context.py
python3 scripts/validate-changelog-fragments.py
python3 scripts/validate-legacy-impact.py --feature specs/261-clean-summary-copy-export/spec.md
```

Проверяются все четыре формата итогов отдельно и вместе с расшифровкой,
неизменность сохранённого протокола и работа источников внутри встречи.
Новый Node-тест воспроизвёл ошибку до исправления и прошёл после него.

Перед слиянием дождаться `governance-fast` на точном SHA PR. Полный CI запускает
оператор выпуска для замороженного кандидата. Ручная приёмка установленного
GRAF Dev и проверка production этим набором тестов не подтверждаются.
