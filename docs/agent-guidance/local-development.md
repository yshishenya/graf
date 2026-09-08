# Local Development

## Один установленный GRAF Dev

Ручные проверки интерфейса, записи, устройств, разрешений, уведомлений и
встроенного кабинета выполняются только в `/Applications/GRAF Dev.app` с
bundle ID `pro.2brain.graf.dev`. Автоматические тесты без установки приложения
могут выполняться в worktree. Production GRAF не используется для проверки
незавершённых изменений.

Перед изменением стенда выполни `infra/scripts/dev-harness.sh status --json`:
проверь активный manifest/SHA и согласуй занятость общего стенда с текущей
работой. Далее используй `build → promote → status → smoke` из
[инструкции стенда](../../infra/dev/README.md). Установка и запуск сериализованы
существующей блокировкой. Сборочные артефакты и резервная копия для отката
допустимы внутри harness; самостоятельно регистрировать или запускать их нельзя.

Сохраняй путь, bundle ID, signing identity, designated requirement и entitlements.
Не меняй подпись на ad hoc, не сбрасывай TCC, не редактируй plist/launcher
установленного приложения вручную. При dirty checkout сначала заверши доступные
тесты и авторизованный коммит; не обходи проверку SHA и чистоты checkout.
Ошибка сборки, подписи, разрешений или занятость стенда не разрешает создавать
GRAF Local/Preview/Test или запускать бинарник через `swift run`. Зафиксируй
причину и исправь существующий путь. Отдельная копия допустима только по прямому
указанию пользователя именно на отдельную копию; согласие на запись/уведомление
не отменяет правило единственного Dev-приложения.

`build-local-app.sh` и `run-local-app.sh` оставлены как отказ с понятным
переходом на harness: они не создают и не запускают приложение. Старые временные
копии удаляй только при доказанном владении текущей задачей; чужие приложения,
данные и разрешения не трогай.

## Стенд и его жизненный цикл

The active Dev path is `infra/scripts/start-dev-runtime.sh` through
`infra/scripts/dev-harness.sh`; it owns one `graf-dev` Compose project with
loopback-only API/frontend `http://127.0.0.1:8081`, PostgreSQL `54329`, MinIO
`9002/9003` and Temporal `7233`. It starts API, server-rendered frontend,
Temporal, processing worker and media worker from one exact SHA. The old
`start-local.sh`/`docker-compose.local.yml` path is retained only as a bounded,
non-active compatibility exception until Feature 228 retirement review.

Dev promotion and rollback own the installed app lifecycle. They gracefully
terminate the process launched from `/Applications/GRAF Dev.app`, replace and
re-register the bundle, launch the new candidate, and require
`app_presentation` to prove `GRAF Dev`, channel `dev` and the distinct
Dev-badged icon. Do not run `install-dev-app.sh` directly while the app is
running; it intentionally fails closed. Compensation relaunches the previous
app only when it was running before the transaction.

Login uses the existing email-code flow with `local@graf.test`. Development code
and the non-Secure `graf_dev_owner_session` cookie are enabled only by the local
script; production keeps the existing `__Host-` Secure cookie.

The Dev Compose profile keeps MediaScribe unconfigured by default. Processing
worker pollers still start and are readiness-testable; an actual processing
activity fails closed with `blocked_config` and makes no provider request until
an operator supplies the server-side provider configuration. This exception is
development/test-only; production provider configuration remains mandatory.

## Имена совместимости

`GRAF Local Code Signing` — имя уже используемого сертификата GRAF Dev,
а не отдельное приложение. Не переименовывай и не заменяй его: это нарушит
сохранение разрешений. `GRAF_LOCAL_APP` пока остаётся внутренним признаком
ограничения адресов loopback для Dev и старых конфигураций; это не команда
создания приложения. Исторические release/evidence документы сохраняют
фактические названия проверявшихся сборок. Старый канал `disposableLocal`
сохранён только для чтения прежней конфигурации; новых сборщиков для него нет.
Имена `local` в записи, очереди, email тестового аккаунта и подписи релиза
не означают отдельный тестовый продукт и не подлежат механической замене.

## Изменение управляющего кода стенда

Если promote сообщает `runtime definition differs`, используйте штатный
`--previous-checkout` с чистой временной рабочей копией активного полного SHA
из того же Git-репозитория. Harness сверяет SHA, байты управляющих файлов и
сохранённый digest до остановки. Прежний адаптер выполняет восстановление
своими закреплёнными образами; новый контроллер проверяет полный smoke.
Образы PostgreSQL/MinIO/Temporal должны совпадать. При одинаковой схеме
используется прежняя процедура. При доказанном переходе к новой схеме harness
сохраняет холодную пару полных томов PostgreSQL/MinIO и долговечный журнал.
Неизвестные ревизии, неполный граф и смена образов хранилищ остаются отказом.

После прерывания `status` показывает `rollback_required`. Из чистого checkout
целевого SHA выполните `infra/scripts/dev-harness.sh recover-schema`: до запуска
новых writers он восстанавливает прежний стенд, после их допуска — только
целевой стенд с новой схемой. Не запускайте старый harness или startup напрямую:
замороженные старые скрипты не знают нового журнала. Предыдущий checkout
используется только как проверенный адаптер нового контроллера. Не удаляйте
журнал или архивы вручную, не подменяйте observed revision и не делайте downgrade.
Обычные promote/rollback/start/smoke не обходят незавершённое восстановление.

Обратный переход выполняйте из чистого checkout активной версии командой
`rollback --live --manifest-id <предыдущий manifest> --target-checkout <путь>`.
Это рабочая копия исходного кода, не ещё одна установленная версия GRAF.
Не удаляйте и не редактируйте её, пока работающий runtime использует её
`start-dev-runtime.sh`, в том числе после восстановления при ошибке.
После успешного возврата на основной checkout временную копию можно удалить
через `git worktree remove`. Никогда не переписывайте runtime digest и не
останавливайте стенд для обхода проверки совместимости.

Если серверные компоненты остановились после завершённой операции, повторный
`promote --live` неизменного активного manifest из его чистого checkout
восстанавливает эту же версию. Не редактируйте parent/SHA manifest. Временная
ошибка опроса Docker не должна останавливать работающие службы; причину
завершения управляющего процесса ищите в техническом журнале harness.
