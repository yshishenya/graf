# Проверка реализации F262

Статус: основной код опубликован в PR #6911; итоговые исправления проходят приёмку. Фактические результаты и незакрытые проверки — в [evidence.md](evidence.md); наличие команды ниже само по себе не означает PASS.

## Подготовка

1. Прочитать [spec.md](spec.md), [contracts/lifecycle.md](contracts/lifecycle.md), [scenarios.md](scenarios.md).
2. До сборки/запуска прочитать `docs/agent-guidance/local-development.md`; использовать только `/Applications/GRAF Dev.app` через штатный dev-harness. Если приложение/сессия недоступны, записать BLOCKED; не делать отдельную копию.
3. Поднять предусмотренное проектом тестовое окружение с disposable PostgreSQL/storage; только синтетические workspace/device/recording fixtures. Не использовать пользовательские тестовые записи как разрешённый объект удаления без отдельного указания.
4. Создать связанные local-only, create-unresolved, uploading, server+local и server-only примеры, две сессии/устройства. Для конкуренции управляемо задерживать create, part, finalize, delete response и ACK.

## Быстрые команды по существующим тестам

Из корня репозитория; использовать установленное проектное окружение Python/Swift, не устанавливать новые зависимости ради этой проверки:

```sh
git diff --check
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd apps/server
uv run pytest tests/integration/test_cabinet_hx_delete_feedback.py tests/integration/test_deletion_lifecycle_blocks_access.py tests/integration/test_local_purge_coordination.py tests/integration/test_recording_sync_conflicts.py tests/integration/test_recording_workflow_deletion_races.py
```

Browser baseline использует существующий `apps/server/tests/browser/mixed-meeting-list.test.cjs`; запускать командой проекта с его Playwright environment. Swift baseline — `DesktopUploadQueueV5Tests`, `DesktopMeetingShellWebViewBoundaryTests`, `DesktopLocalPurgeTests`, `DesktopUploadCustodyProjectionTests`. При реализации добавить минимальные тематические тесты к существующим наборам, а не отдельный тестовый framework.

## Новые обязательные доказательства

- Табличная проверка общего lifecycle rule: deletion/access/intent/upload/purge + generation; stale response не снимает terminal state.
- PostgreSQL concurrency check create↔cancel-origin в обоих порядках, включая старый create API; после commit нет live Meeting при accepted cancellation. Проверить RLS, повторные запросы и namespace collisions.
- Browser interaction check полного delete→response→HTMX swap→native projection→selection/count/empty/focus, а не проверка наличия строк исходного кода.
- Native filesystem check durable intent перед HTTP; безопасные пути; частичная очистка; crash перед/после ACK; corrupted queue без автоматического rescan-upload.
- Device check expired/failed→verified ACK; новая регистрация получает отдельное задание и не подтверждает старое.
- GRAF Dev real UI check local playback stop после удаления; внешнее приложение не используется как управляемый preview.
- Сценарии S01–S51 сопоставить с результатами; непроверенное/blocked не отмечать PASS.

## Нагрузка и время

SC-002 измерить от получения authoritative receipt/remote state до закрытия строки/управляемого контента. SC-003 измерить двумя активными сессиями на видимой записи; задержку сервера и polling учитывать отдельно. SC-006 — 100 синтетических локальных пакетов до 100 МБ; повторить в условиях файловой ошибки и проверить честный pending/failed. Нельзя объявлять p95 по одному запуску; сохранить число измерений и среду.

## PR и выпуск

Пройдены проектирование, независимая проверка требований, tasks/analyze, создание issues и реализация. Итоговый независимый review не выявил новых дефектов. S02 завершён в области UI/server/native queue/filesystem; C1/C2 принимаются по совокупному evidence. Итоговые SHA-bound проверки PR и tracker closeout выполняются отдельно. Для PR обязательный `governance-fast` на точном SHA; локальный scoped/fast — по действующему порядку диагностики. Для frozen release candidate — один авторитетный `release-full`, затем разрешённые release/deploy gates. Public macOS требует notarization, stapling, Gatekeeper, Sparkle и фактическую проверку установленной версии.

Server capability и миграцию выпускать до нового клиента. После нового клиента выполнить legacy reconciliation, затем проверить installed app; факт публикации не равен установке. Production не изменялся. GRAF Dev установлен на `0e19ba345450f18fded8ff7a5b1c7e1640a8a153` штатным harness, smoke **13/13 PASS**. VoiceOver лично проверен пользователем. Совместимый rollback db76→43f→db76 сохраняет v3/0092 и 78/17/1; подробности и post-restore API429 — в evidence.md.

Установленный S02 подтвердил одну связанную server+local строку, принятое удаление и отсутствие local alias. После исправления ошибочного origin только собственной fixture и штатного rollback/возврата 0e19 приложение перезапущено и автоматически повторило purge: terminal_deleted, server_meeting_deleted, retainedfalse, файлы отсутствуют. S02 принят по UI до перезапуска и настоящим persisted queue/filesystem после него. GUI после перезапуска не наблюдался из-за блокировки Mac. Подробности в evidence.md и /tmp/graf-262-linked-acceptance.json. SC-002: 994 мс для строки в отдельном local-only наблюдении; managed player и файлы проверены отдельно. Общая высокоточная метрика всех эффектов не заявляется.

Для S06/S08/S18 использовать добавленные PostgreSQL concurrent test и Chromium `threeTypes`/`offlineCopy` вместе с native boundary tests. S08 проверяет offline Chromium и отображение native контракта; долговечный native intent/restart проверяются Swift, физическое отключение сети Mac не выполнялось. Old/new compatibility проверяется контрактами; неподдерживаемые бинарники не устанавливать поверх v3 queue. Полное операторское восстановление backup — отдельный release gate.
