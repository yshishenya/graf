# F273/T113 local_only: независимое ревью кода — 29.10.2026

**SCOPED PASS.** В проверенном замороженном diff шести файлов дефектов P1/P2 или блокирующих отклонений от принятого узкого scope не найдено. Это приёмка локальной подготовки режима, пустых намерений получателей и общего HTTP admission; не готовность всего T113 или рабочего измерения.

## Источник и границы проверки

Reviewer `/root/f273_release_boundary`. Основа `5c1ab517a194b5102a4fbefa732840e071717841`, ветка `codex/f273-local-period-20261029`, текущий незакоммиченный diff, high-risk-product, существующая T113. Проверено задание `.dev/growth/t113-local-only-code-review-request-20261029.md`, весь diff четырёх исходных и двух тестовых файлов, окружающие валидаторы/HTTP handler/общий ingest/legal gate, неизменный SQL helper и maintenance delivery selection, серверный auth caller. В scope не включены чужие параллельные docs/fragment правки.

Действует докодовый PASS из `t113-local-only-review-20261029.md` и прежний A/R3. Код, требования, чек-листы, Git/GitHub, рабочая среда и данные не менялись. Тесты, сборки и контейнеры ревьюер не запускал. Изменён только данный отчёт.

## Проверенные пути

1. **Настройки всех сред.** Field-validator принимает нормализованный local_only; отдельный model-validator расположен вне production-only проверки. Единый predicate требует enabled=true, provider_mode=disabled и выключенные PostHog master, оба продуктовых Яндекс-пути, desktop-direct, direct egress и replay. Production исключение из прежнего обязательного provider_mode узко привязано к local_only; другие значения сохраняют прежние условия. Неактивные defaults автосбора не включают передачу при выключенном master. Метод live_provider_delivery_allowed явно возвращает false в local_only даже при всех прежних approvals=true.
2. **Свежая граница приёма.** Изначальное validation_mode сохраняется перед первым gate. В callback, вызываемом SQL helper после реального identity lock и перед INSERT, проверяются неизменность режима и свежий activation_milestone_write_blockers. Для local_only дополнительно вызывается единый конфигурационный predicate; разрешающий тестовый gate не превращает испорченные flags в намерение доставки. На отказе сессия завершается/откатывается до возвращения admission_blocked.
3. **Пустые получатели.** Ветка local_only возвращает () до resolve_provider_delivery_gate и YandexOfflineConversionExporter.from_settings/transfer_decision. Неизменный SQL helper строит not_requested/not_requested и соответствующие reason; ingest не вызывает транспорт. Неизвестная первая веха/субъект/trigger и неподходящая авторизация по-прежнему отклоняются до DB admission.
4. **Два HTTP-формата.** /events продолжает пользоваться общим ingest. Изменение внешней проверки /posthog-desktop-capture допускает local_only без включения desktop egress, но сохраняет product_analytics_enabled, telemetry_gate_state, api_key_state, payload/catalog проверки и общий trusted-principal admission. В остальных режимах прежняя конъюнкция provider/desktop/egress flags сохранена. Обхода через прямой PostHog вызов нет; формат запроса не превращается в новый источник доверия.
5. **Повтор после смены режима.** SQL остаётся INSERT ON CONFLICT DO NOTHING с последующим чтением исходного решения. Свежие намерения, вычисленные при повторном входе в другом режиме, не обновляют старую строку. not_requested не входит в maintenance selection/claim для pending/pre_send_retry; hidden replay старого local-only решения не добавлен. Идентификатор, payload/кампания/время прежней строки сохраняются. Само событие и состояние доставки не подменяются HTTP успехом.
6. **Server-auth и отказ измерения.** Серверный account-connected вызывает тот же ingest после продуктовой транзакции и сохраняет прежнюю изоляцию ошибки измерения от входа. Local_only не открывает ещё непроверенные result/value triggers T112.
7. **Рабочий HOLD.** activation_milestone_write_blockers по-прежнему безусловно добавляет activation_recovery_unverified после действующих legal/disclosure/register/operations проверок. Новый код добавляет только конфигурационный blocker и не создаёт разрешающего recovery пути. Provider delivery продолжает иметь отдельные live_safe/flags/approval gates. Оператор/история/restore/readiness/fence этим diff не принимаются.

## Проверки и пределы доказательств

Ревьюер прочитал тесты и журналы родительского агента; повторных запусков не было.

- До реализации двадцать новых конфигурационных случаев дали `20 failed, 8 deselected, 2 warnings in 0.22s`. Это положительные и отрицательные случаи local_only в development/production, отсутствующего ранее значения.
- После реализации существующий изолированный PostgreSQL runner собрал138проверок и получил **138 passed,2warnings,8.27с**; `postgres_test_result=pass`, `postgres_test_cleanup=isolated_container_removed`. Ruff всех шести файлов: **All checks passed!**
- HTTP и server-auth положительные проверки явно заменяют всё ещё закрытые эксплуатационные gates только внутри процесса теста. В local_only resolver/exporter заменены аварийными заглушками; успешное принятие одной строки и неизменность not_requested проверены чтением PostgreSQL. Transport-заглушки также запрещают передачу в admission.
- Проверка ожидания identity получает настоящий PostgreSQL backend PID и наблюдает wait_event_type=Lock. После этого меняется режим или yandex flag; после release транзакция получает admission_blocked, строк нет. Так проверяется порядок, а не только вызов callback без ожидания.
- Варианты отсутствующего/чужого principal, неподтверждённых триггеров, declined telemetry и клиентского ключа проверяются для обоих HTTP форматов/режимов. Повтор в provider_smoke с искусственно разрешённым provider gate остаётся duplicate, одна строка и оба not_requested.
- Отдельный HTTP/server-auth сценарий без isolated_admission получает403/admission_blocked и ноль строк. Он сохраняет также другие рабочие blockers; самостоятельный unit-сценарий убирает operations blockers, даёт читаемый basis register и непосредственно подтверждает оставшийся activation_recovery_unverified. Поэтому HTTP-отказ не выдаётся за доказательство единственной причины recovery.
- Проверки доказывают поведение рассмотренного учебного среза. Они не доказывают действующую готовность реальной БД, непрерывность исторических источников, actual restore, filesystem fence вокруг сессии или коммерческую активацию.

## Контрольные суммы проверенной версии

После чтения исходников и diff все девять хешей совпали с предоставленным tested-hashes manifest. До записи этого отчёта проверка совпадения выполнена повторно.

| Путь | SHA256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/config.py` | `2cd24aff502295b9eabbdf5ddbdbf853466f63b10c67cf3cbdf00fd426e3cfeb` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `a37f46e7b750945d1559a1d8b7ac7022613d7135af643e88f79a57d055151cb6` |
| `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py` | `578de74b6a8362de6c73de9e2bca79e7fd60774324966dae2086d2b6daf7644e` |
| `apps/server/src/twobrain_rec_server/api/product_analytics.py` | `37efb4a4a557c728f3143411204124869b0451771586ea54262b6425082dc296` |
| `apps/server/tests/unit/test_product_analytics_provider_config.py` | `d64dc6f6225dc19b5b7b8f3a8b423e5eab8fc44bf81acc25e7de21bd96800a7c` |
| `apps/server/tests/contract/test_activation_milestone_ingress.py` | `8a3cd1e04cb682dc22134c634d1325625c98c3fc659b36c434cf1c492d8d3867` |
| `.dev/growth/t113-local-only-final-20261029.log` | `3274989d3f80f8a1fb0ae561b6475dfe4a3cd734d9973b08afb2383224b3bb0e` |
| `.dev/growth/t113-local-only-lint-20261029.log` | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `.dev/growth/t113-local-only-red-20261029.log` | `086bd94f8b8f6f6fad829e70eea02b2e7cad50fab90148f881cab5b07beee8e6` |
| `.dev/growth/t113-local-only-tested-hashes-20261029.json` | `8de3c74758131535147be3f29e83ec1fd7fc420b816710bb72c2a1569a360e7f` |

## Чек-листы и остаток

В этом code review отметки не пересматривались и не менялись; актуальные хеши совпали с докодовым чтением всех117вопросов:

| Чек-лист | Отмечено / не отмечено | SHA256 |
| --- | --- | --- |
| `requirements.md` | 16 / 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| `privacy-measurement.md` | 45 / 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| `security.md` | 27 / 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| `infra.md` | 29 / 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Итог117/0 остаётся оценкой качества требований. T113/T112, включение writer, доверенный оператор A/R3 и рабочие проверки восстановления остаются открытыми. Нового PR/Full/CD или отдельного выпуска этот отчёт не требует и не подтверждает. После изменения любого из шести проверенных файлов данный code-review вывод нужно привязать к новой версии повторной проверкой.
