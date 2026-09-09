# Проверки F256

## Исходный результат

2026-09-08 до реализации:14 passed,151 deselected в focused playback/speaker suites.
Это только baseline. Ножницы и серверная обрезка вне первого этапа.

## Проигрыватель

Из apps/server:

```sh
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_static_assets_contract.py tests/unit/test_cabinet_web_shell.py -k 'playback or speaker_timeline or speaker_rename or speaker_ui'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

Из корня запустить существующую геометрию F205 и новый сценарий F256:

```sh
node specs/205-playback-panel-layout/evidence/playback-layout-runtime-check.cjs
node specs/256-krisp-playback-panel/evidence/playback-panel-runtime-check.cjs
```

GRAF_NODE_MODULES указывает на реально установленный playwright при необходимости;
GRAF_BROWSER=webkit выбирает второй движок. Пути окружения в git не сохраняются.
Синтетический WAV создаётся на время в тесте; реальные записи не используются.
Проверить play/pause, все скорости, ±15 и Shift+стрелки, выбранные спикеры с
перекрытием/паузой, окончание, canvasless timeline, avatar navigation, collapse,
resize мышью/клавиатурой, ошибку play, замену main и переименование без нового audio.
Проверить обе темы, 390/768/787/788/991/992/1440 px и 200%; controls gap/overlap,
доступный фокус/Escape и reduced motion. Допуски2 px/100 ms.

## Комментарии и права

```sh
bash apps/server/scripts/run_local_postgres_tests.sh -q tests/integration/test_meeting_comments.py tests/integration/test_meeting_share_links.py tests/integration/test_notification_inbox_flow.py tests/integration/test_account_merge.py tests/integration/test_deletion_lifecycle_blocks_access.py
```

Изолированный Postgres; тесты не подключаются к рабочим данным. Требуется полный
create/reply/edit/react/resolve/reopen/delete, сохранение после перезагрузки,
owner/viewer/commenter/editor/summary-only, отзыв перед POST, CSRF, RLS producer,
cross-workspace UUID, stale revision, request retry, mentions без доступа,
удаление встречи и account merge. Проверить внутреннюю карточку без email.

## Репозиторий и установленное приложение

```sh
git diff --check
infra/scripts/ci-local.sh --fast
infra/scripts/dev-harness.sh status --json
```

Для GRAF Dev после разрешённого validated commit использовать build→promote→status→smoke
по docs/agent-guidance/local-development.md и infra/dev/README.md. Dirty checkout
не обходить; отдельные приложения не создавать. Пройти основные команды и
VoiceOver в /Applications/GRAF Dev.app. Browser embedded не заменяет этот gate.
Коммит, PR exact-SHA governance-fast, Full CI и выпуск — отдельные результаты;
пропущенные/заблокированные gates не помечать PASS.
