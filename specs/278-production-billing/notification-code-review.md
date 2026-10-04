# Независимое ревью кода T032

Дата: 2026-10-04. Ветка `codex/278-billing-mail-delivery`, база `201f64bbef208a378239a190ecff1024c7ab5ab5`; проверены текущие рабочие изменения. Рецензент изменяет только checklist и отчеты, без кода, финансовых данных, runtime, GitHub, коммитов и выпуска.

**PASS текущего кода T032 в проверенной области. NTF-C02 устранен и проверен.** Качество требований подтверждено отдельно: notification-delivery 10 checked / 0 unchecked.

## Первоначальный NTF-C02: нераспознаваемый JSON Postal допускал повторный POST

`apps/server/src/twobrain_rec_server/auth/email_delivery.py`, `_post_message`, ветка после response.json: HTTP 200 с `{}`, `[]` или неизвестным `status` переводится в `EmailLoginDeliveryError("postal_delivery_rejected", retryable=True)`, по умолчанию outcome_unknown=False. Такой ответ не доказывает отказ сервера принять письмо. Новый sender трактует его как известный безопасный отказ, возвращает строку в retry и повторяет POST до пяти раз. Это нарушает plan T032/NTF009 для malformed/unknown.

Независимое воспроизведение через реальный PostalEmailLoginClient и httpx.MockTransport (synthetic, без сети/отправки) подтвердило все три результата: `postal_delivery_rejected retryable=True outcome_unknown=False`. Существующий unit malformed тест покрывает только невалидный JSON `not-json`; sender тесты подменяют всю send функцию и не ловят ошибку классификации.

Нужна проверяемая граница: только явный распознаваемый отказ `status=error` допускает известный retry; нераспознаваемая структура/статус — `postal_malformed_response`, outcome_unknown=True/retryable=False. Требуются unit parser и PostgreSQL sender проверки с настоящим клиентом и подменой только внешнего HTTP транспорта. Исправление передано основному агенту; reviewer код не меняет.

## Подтвержденные свойства

- Maintenance сохраняет DB роль, RLS/context, read-only/cap_drop/no-new-privileges, приватные права и группу, отсутствие публичных портов/CSRF/MediaScribe. Добавлены существующие Postal secret/сеть и согласованные настройки, включая обязательный production bootstrap workspace и public_base_url. Производственный валидатор не ослаблен.
- Readiness до runtime_mutated запускает новые образы через compose run с заменой команды на python probe; worker не запускается. Повторный exec проверяет три фактических службы до dispatch gate. Probe читает настройки/непустой ключ и TCP, без HTTP POST/send/SQL/финансовых изменений. Связность не доказывает действительность ключа/TLS/HTTP/API/доставку.
- При активном checkout/observation и выключенной почте CD блокируется; enabled проверяет каждую службу. Вывод ограничен фиксированным result/reason и фиксированным именем службы, дочерний stdout захвачен и stderr подавлен. Чувствительный exception text не попадает в логи sender/цикла.
- Sender под FOR UPDATE повторно допускает только pending/retry, фиксирует failed/postal_outcome_unknown и attempts до send, освобождает транзакцию до сети. Конкурирующий sender видит failed и пропускает. Cancellation/crash до записи успеха сохраняет unknown без автоматического повтора.
- Только известная безопасная retryable ошибка повторяется в лимите пяти. При успехе delivered означает принятие Postal по существующему контракту; это не inbox. Event/recipient/workspace и финансовые поля не меняются; исторические failed/delivered/suppressed не сбрасываются и не выбираются для отправки.

## Текущие доказательства

Непосредственно прочитан новый `.dev/billing-mail-acceptance/focused.log`: **163 passed, 2 warnings, 9.98 s**, `postgres_test_result=pass mode=focused`, `postgres_test_cleanup=isolated_container_removed`. Семь файлов: billing_notification_flow, compose_hardening, deployment_readiness_gates, email_login_delivery, billing_notifications, notification_preferences, billing_maintenance. Сценарии проверяют success/known retry/предел/nonretryable/unknown/generic/cancellation/concurrent/suppressed, согласованность Compose, production validator, конфигурацию и безопасный вывод. Этот PASS не закрывает NTF-C02; требуется исправление и новый результат.

163 — новый результат текущей базы. Старые 144/146/164 из удаленных /tmp журналов относятся к прежним проходам и не используются как актуальное доказательство. Это реальные локальные PostgreSQL транзакции с синтетическим внешним транспортом; SIGKILL процесса, live Postal, ящик получателя и production RLS probe reviewer не выполнял. Сохранение роли/RLS подтверждено diff/исходниками, отдельная новая live RLS приемка не заявляется.

Требования перечитаны: **10 checked / 0 unchecked**; все checklist прочитаны: 74/0 всего, 58/0 reviewer-owned. T032 остается открытой до нового exact-SHA PR/full release и фактического Postal accepted/получения письма. Исторические строки — отдельный ограниченный dry-run и сверка; новых списаний не требуется. Предшествующие T031 и годовой чек не переоткрываются.

## Уточнение NTF010 до патча parser

Перечитаны новые plan/tasks и пять unit/три PostgreSQL sender сценария с реальным PostalEmailLoginClient/MockTransport. Требование сформулировано достаточно: только документированные success/error; отсутствующий/неизвестный status, неверная структура остаются outcome_unknown без повтора. [Официальная документация Postal](https://docs.postalserver.io/developer/api/) подтверждает два значения status. Прочитан `.dev/billing-mail-acceptance/parser-before.log`: **5 failed, 13 deselected** — требования регрессии ловят исходный дефект. Это ожидаемый красный этап, не PASS кода. Checklist после добавления и перечитывания: **10 checked / 0 unchecked, PASS требований**. Исправление общего parser и повторные проверки еще нужны.

## Повторная проверка после исправления NTF-C02

Перечитан актуальный минимальный diff общего Postal parser: не-dict или status вне tuple success/error дает postal_malformed_response, retryable=False/outcome_unknown=True; tuple корректен также для status=list. Только явный error дает прежний известный отказ; success сохраняет существующий контракт принятия. Это соответствует [официальной документации Postal](https://docs.postalserver.io/developer/api/) и NTF010. NTF-C02 закрыт локально.

Прослежены все пять методов, использующих _post_message, и текущие callers. Login и admin обрабатывают тот же EmailLoginDeliveryError; invitation и account-created уже различают outcome_unknown и задают non_retryable для Temporal, API приглашения тоже возвращает outcome_unknown отдельно. Адресаты, payload, HTTP маршрут и финансовые вызовы не менялись. Новый parser исправляет общий источник классификации, без дублирующих guards.

Непосредственно прочитаны завершенные новые журналы после патча:

- `.dev/billing-mail-acceptance/focused-final.log`: **171 passed, 2 warnings, 11.69 s**, collection_count=171; focused PostgreSQL PASS и isolated_container_removed. Семь прежних файлов плюс пять новых parser cases и три sender случая настоящего Postal client/MockTransport. Нераспознаваемые object/list/unknown ответы в sender имеют ровно один вызов и сохраняют failed/postal_outcome_unknown, неизменные identity/recipient/финансы.
- `.dev/billing-mail-acceptance/related-final.log`: **18 passed, 2 warnings, 0.07 s**, collection_count=18; смежные invitation/admin проверки, focused PASS и isolated_container_removed.
- Reviewer повторно выполнил `bash -n infra/scripts/cd-remote-runtime.sh` и `git diff --check`: PASS. Прочитан F278 changelog fragment: только T032/#7524, без повторного закрытия T031 и без неподтвержденной доставки.

163 PASS — прежний этап до патча parser, 5 failed — исходный красный этап, 171 и 18 — завершенные текущие наборы; эти числа не заменяют друг друга и не объявляются общим выпуском. Новых конкретных блокеров по текущему diff не найдено.

После записи notification-delivery перечитан: **10 checked / 0 unchecked, PASS требований**. Все checklist прочитаны: **74 checked / 0 unchecked**, reviewer-owned **58/0**. Code PASS относится к незакоммиченному diff поверх указанной базы; после нового source SHA обязательны exact-SHA PR и полный выпуск. T032 целиком остается открытой до production проверки, Postal accepted и фактического получения письма. Живых отправок, новых списаний, reset старых failed, GitHub/commit/deploy reviewer не выполнял.
