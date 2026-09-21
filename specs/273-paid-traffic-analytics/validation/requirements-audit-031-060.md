# Независимая проверка покрытия требований FR-031 … FR-060

Это независимая проверка: для каждого требования второй половины спецификации
найдено место реализации, найден тест, и тест прочитан целиком, чтобы понять,
проверяет ли он именно это требование, а не упоминает тему.

Дата проверки: 2026-09-19.

Ветка: `273-paid-traffic-analytics`, рабочее дерево
`.dsh-worktrees/paid-traffic-analytics`, коммитов фичи нет, проверялась рабочая
копия.

Как проверялось: чтение `specs/273-paid-traffic-analytics/spec.md`, затем
поиск по дереву (`grep -rn`) по коду, тестам, инфраструктурным скриптам и
документам; каждый тест, названный в таблице, открыт и прочитан. Тесты не
запускались; там, где вердикт опирается на поведение, приведена цитата из кода
теста. Имена тестов не выдуманы: тест, которого нет, помечен как отсутствующий.

Требование FR-030 не входит во вторую половину по нумерации, но проверено
дополнительно, потому что оно прямо названо в задании на проверку.

Вердикты: «покрыто», «реализовано без теста», «тест без реализации»,
«не найдено», «документ вместо реализации», «противоречие».

## Таблица

| Требование | Вердикт | Реализация (файл) | Тест (файл::имя) | Чем подтверждено |
| --- | --- | --- | --- | --- |
| FR-030 | покрыто | `infra/scripts/alert-analytics-degradation.sh`; `infra/posthog/graf-analytics-degradation-alert.service` и `.timer`; `infra/posthog/alert-rules.txt` | `apps/server/tests/contract/test_analytics_degradation_alerting.py::test_guard_state_feeds_the_alert_end_to_end`; `::test_scheduled_alerting_units_exist_with_the_reviewed_cadence` | Тест подставляет поддельный `curl`, читает журнал доставки и тело сообщения: `assert "alert_result=delivered" in result.stdout`, `assert "analytics-oncall" in message`, `assert "delivery_deadline_minutes: 15" in message`. Канал (api.telegram.org) лежит вне измеряемого сервера, таймер опрашивает состояние охраны раз в 5 минут. Частичный пробел: живого срабатывания и учения на стенде не было (см. ниже) |
| FR-031 | покрыто | `infra/scripts/posthog-runtime-guard.sh` (`add_analytics_breach`/`add_analytics_disable` против `add_host_breach`); поле `scope` в `infra/posthog/alert-rules.txt` | `test_analytics_degradation_alerting.py::test_guard_splits_analytics_and_host_scopes`; `::test_guard_disables_measurement_only_from_analytics_scope`; `apps/server/tests/unit/test_product_analytics_degradation_order.py::test_only_analytics_scope_reasons_may_disable_measurement` | Проверяется сам текст скрипта: `assert 'if [[ -n "$analytics_disable_reasons" ]]; then' in script`, `assert 'host_disable_reasons' not in script`, и что в ветке отката нет `host_breaches`. Ветка отключения измерения действительно заведена только на область аналитики. Проверка статическая: живого роста трафика на сайт не было |
| FR-032 | покрыто | `infra/scripts/posthog-runtime-guard.sh` (список ключей только измерения); `apps/server/src/twobrain_rec_server/product_analytics/readiness.py` | `apps/server/tests/unit/test_product_analytics_degradation_order.py::test_the_product_answers_over_http_while_measurement_is_disabled`; `::test_the_guard_switches_off_measurement_and_nothing_else` | Реальный HTTP-прогон приложения с выключенным измерением: `assert live.status_code == 200`, `assert live.json() == {"status": "ok"}`; маршруты измерения отказывают (`assert ingest.json()["code"] == "product_analytics_disabled"`). Скрипт охраны не трогает ключи продукта: `assert key not in script` для `TWOBRAIN_DATABASE_URL`, `TWOBRAIN_INGEST_ENABLED`, `TWOBRAIN_CABINET_ENABLED` |
| FR-033 | покрыто | `infra/scripts/backup-posthog.sh`; `infra/posthog/graf-posthog-backup.service` и `.timer`; `infra/posthog/backup.env.example`; `infra/posthog/backup-volumes.txt` | `apps/server/tests/contract/test_analytics_retention_enforcement.py::test_backup_archives_every_required_class_and_ships_one_copy_offsite`; `::test_scheduled_scripts_are_valid_and_documented`; `test_analytics_degradation_alerting.py::test_scheduled_alerting_units_exist_with_the_reviewed_cadence` | Скрипт запускается на подставном docker: `assert "backup_result=pass" in result.stdout`, `assert "copies_offsite=1" in result.stdout`, расписание `OnCalendar=*-*-* 02:30:00`. Частичный пробел: конкретное целевое хранилище в репозитории не названо (см. ниже) |
| FR-034 | покрыто | `provider_readiness.py::collect_analytics_operations_evidence`, `::analytics_operations_blockers`, `::operations_block_claim` | `apps/server/tests/integration/test_product_analytics_provider_readiness_blockers.py::test_readiness_blocks_when_the_newest_copy_is_stale`; `::test_live_provider_delivery_claim_requires_fresh_operations_evidence` | Устаревшая копия блокирует: `assert "backup_stale" in state["blockers"]`; без доказательств готовность заблокирована: `assert blocked["verdict"] == "blocked"`, `assert "analytics_operations_not_ready" in blocked["blockers"]`. Частичный пробел: ветка `backup_missing` (файл состояния есть, успешного прогона нет) не покрыта ни одним тестом |
| FR-035 | покрыто | `infra/scripts/verify-posthog-restore.sh`; `infra/posthog/graf-posthog-restore-verify.service` и `.timer` | `test_analytics_retention_enforcement.py::test_restore_verification_replays_a_stored_copy_without_touching_the_live_stack`; `test_analytics_degradation_alerting.py::test_scheduled_alerting_units_exist_with_the_reviewed_cadence` | Восстановление проигрывается и результат фиксируется как доказательство: `assert "restore_verification_result=pass" in result.stdout`, `assert evidence.exists()`, `assert "content_policy=metadata_only_no_visitor_or_user_data" in evidence_text`. Расписание `OnCalendar=*-*-01,15 04:30:00` закреплено тестом. Частичный пробел: проверка идет на подставном docker, живого узла не касается |
| FR-036 | противоречие | `apps/server/src/twobrain_rec_server/product_analytics/retention.py` (правила 365/1095 дней); `infra/scripts/enforce-product-analytics-retention.sh`; `infra/scripts/apply-posthog-event-ttl.sh`; `infra/posthog/clickhouse-retention.sql` | `test_analytics_retention_enforcement.py::test_retention_execution_deletes_by_age_and_logs_every_deletion`; `::test_retention_terms_match_the_approved_contract` | Тест не проверяет требование: подставной docker отвечает `t` на любой запрос `to_regclass` (`if "to_regclass" in joined: print("f" if FAKE_TABLE_MISSING == "1" else "t")`), поэтому тест проходит при любом списке кандидатов. Реальные таблицы в схеме называются иначе, и ни одно имя не совпадает со списком кандидатов скрипта: агрегаты и атрибуция не удаляются никогда, а готовность аналитики блокируется навсегда. Подробно в разделе «Пробелы» |
| FR-037 | документ вместо реализации | только текст: `docs/analytics/product-analytics-posthog-runbook.md`, раздел «Two Operators And Mandatory Second Factor». В коде состояние доступа — константа `"rbac_audit": "documented"` в `product_analytics/readiness.py` | `test_analytics_degradation_alerting.py::test_documentation_keeps_the_scope_split_and_the_delivery_deadline` — только подстрока заголовка | Тест утверждает лишь наличие заголовка: `assert "Two Operators And Mandatory Second Factor" in runbook`. Ни подсчета операторов, ни проверки членства, ни проверки второго фактора в дереве нет; поиск по `totp`, `mfa`, `second_factor` в `apps/server/src` не находит ничего |
| FR-038 | документ вместо реализации | только текст: `docs/analytics/product-analytics-posthog-runbook.md`, абзац про периодический обзор доступа (соответствие установленной копии охраны репозиторию). Версионирования конфигурации аналитики в коде нет; есть только `product_analytics_yandex_inventory_version` в `config.py` — это версия инвентаря страниц Метрики, а не версия конфигурации аналитики | теста нет: ни один тест в дереве не проверяет FR-038 и не сверяет установленную копию с репозиторием | Ни скрипта сверки (хеш, ревизия), ни теста. Требование закрыто абзацем текста |
| FR-039 | документ вместо реализации | инструмент: `infra/scripts/measure-posthog-storage-growth.sh`; таблица результатов: `docs/analytics/product-analytics-capacity-baseline.md` (все значения `pending operator receipt`); факт непроведения: `specs/273-paid-traffic-analytics/tasks.md` строка 80 (T076 не отмечена) и `specs/273-paid-traffic-analytics/validation/quickstart-evidence.md`, раздел «Что не проверено», пункт 1 | `test_analytics_retention_enforcement.py::test_storage_growth_measurement_reports_the_documented_keys` | Тест проверяет только набор ключей отчета (`absolute_bytes`, `projected_bytes_36_months` и прочие) и строку `pending operator receipt` в документе, а не измеренный объем. Нагрузочной проверки не было, инструмента создания нагрузки (k6, wrk, ab и подобных) в дереве нет вовсе |
| FR-040 | документ вместо реализации | определения: `infra/analytics/dashboards/catalog.json`, `infra/analytics/dashboards/posthog/dashboards.json`, `infra/analytics/dashboards/yandex/reports.json`. Сами определения заявляют, что отчеты не построены: `data_availability.status = "not_fillable_today"`, `apply.requires_operator = true` | `apps/server/tests/contract/test_product_analytics_report_catalog.py::test_report_set_meets_the_minimum_and_covers_every_owner_question`; `test_product_analytics_report_dashboards.py::test_posthog_definitions_cover_every_catalog_report` | Тесты парсят JSON: `assert slug in slugs` для каналов, воронки, объявлений, посадочных страниц и здоровья доставки. Ни один дашборд не применен, ни один отчет не построен; серверный код `catalog.json` не читает (поиск по `apps/server/src` не находит ссылок на него) |
| FR-041 | тест без реализации | реализации нет: ни серверного кода, ни скрипта, который соединяет расход рекламного кабинета с конверсиями; есть только описание в `catalog.json`, раздел `cost_join` | `apps/server/tests/unit/test_product_analytics_report_cost_per_result.py::test_cost_per_activation_is_computed_per_campaign`; `::test_cost_join_metrics_are_declared_for_every_result_kind` | Тест объявляет собственную функцию `cost_per_result` в самом файле теста (эталонная реализация) и проверяет ее: `assert costs == {"brand-search": 2000.0, "generic-search": 7500.0}`. Код продукта в тесте не участвует; вторая половина утверждений — строки JSON |
| FR-042 | документ вместо реализации | `infra/analytics/dashboards/catalog.json` (`reports[].owner`, `caveat_library`), `infra/analytics/dashboards/posthog/dashboards.json` (плитки ролей `caveats`, `freshness`, `completeness`) | `test_product_analytics_report_catalog.py::test_every_report_has_an_owner_freshness_and_mandatory_caveats`; `::test_consent_share_caveat_is_required_on_every_report`; `test_product_analytics_report_dashboards.py::test_caveat_tiles_carry_the_mandatory_caveats_in_words` | Тесты действительно проверяют владельца и обязательные оговорки, но только в определениях: `assert report["owner"]["role"].strip()`, `assert consent_caveat in report["caveats"]`, `assert "нет данных" in rule`. Отчета, к которому требование применяется, не существует |
| FR-043 | документ вместо реализации | `catalog.json`, раздел `metric_vocabulary`: намерение `public_installer_download_clicked`, факт `public_installer_download_aggregate`, активация `first_value_session_completed`; в данных эти сигналы действительно различны (`product_analytics/anonymous_aggregate.py`, `public/analytics.py`) | `test_product_analytics_report_catalog.py::test_reports_separate_download_intent_from_completed_activation` | Тест проверяет словарь и наличие блока `intent_vs_activation` у двух отчетов: `assert intent["event"] != downloads["signal"] != activation["event"]`, `assert slug in separating`. Разделение есть в данных и в определении, но отчета, в котором оно видно, не существует |
| FR-044 | покрыто | `apps/server/src/twobrain_rec_server/product_analytics/approvals.py` (шлюз по записям, виды `legal`, `privacy`, `security`, `qa`, `rollback`, `delivery`, `check`); `readiness.py::build_rollout_readiness_report` | `apps/server/tests/unit/test_product_analytics_launch_approvals.py::test_every_flag_approved_without_records_still_blocks_launch`; `::test_a_complete_register_is_the_only_thing_that_allows_launch`; `::test_a_missing_state_file_approves_nothing` | При всех технических флагах запуск запрещен: `assert campaign_launch_allowed_for_settings(settings, environ=environment) is False`; разрешает только полный набор записей: `assert gate.blockers == ()`, `assert gate.campaign_launch_allowed is True` |
| FR-045 | документ вместо реализации | порядок и требования: `docs/analytics/product-analytics-launch-approval.md`, `docs/analytics/product-analytics-provider-rollback.md`; сам путь отката: `infra/scripts/rollback-product-analytics-providers.sh` и ветка отката в `posthog-runtime-guard.sh`; шлюз: вид одобрения `rollback` в `approvals.py` | `apps/server/tests/contract/test_product_analytics_provider_rollback.py::test_rollback_script_reports_switches_without_state_change`, `::test_execute_is_fail_closed_without_an_operator_executor_hook`, `::test_metadata_only_never_invokes_a_configured_operator_hook`; `apps/server/tests/unit/test_product_analytics_degradation_order.py::test_the_operator_rollback_path_states_the_same_order`; `test_product_analytics_launch_approvals.py::test_an_expired_record_blocks_launch_again` | Контрактный режим теперь явно `--metadata-only` и возвращает `rollback_execution=metadata_only_no_state_change`; `--execute` без явного разрешения и абсолютного исполняемого `TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK` завершается nonzero, а hook в тестах не вызывается. Живого прогона не было: smoke сообщает `rollback_status=metadata_only_not_executed` и `rollback_live_mutation=not_claimed`; запись `rollback` не зафиксирована. Требование «отработан на живом сценарии» по-прежнему не выполнено |
| FR-046 | покрыто для repository docs | `apps/server/src/twobrain_rec_server/product_analytics/consent_copy.py::consent_copy_consistency`, `::read_site_consent_copy`, `::collect_published_consent_documents` | `apps/server/tests/unit/test_product_analytics_consent_copy_consistency.py::test_every_published_document_names_the_runtime_revision`; `::test_a_stale_published_document_is_not_masked_by_another_document`; `::test_a_missing_published_document_is_not_replaced_by_combined_text`; `::test_the_report_names_what_it_cannot_verify` | Страницы рендерит реальное приложение, а каждый repository document отдельно проверяет точную редакцию `2026-09-15.1`. Stale/missing копия получает divergence по собственному пути; внешние копии документов и настройки провайдера остаются операторскими подтверждениями. |
| FR-047 | покрыто | `approvals.py`: виды `legal` и `privacy` с требованием FR-047 и ролями `product_owner` и `privacy_reviewer`; `legal_basis_lifecycle.py::measurement_level_basis_states`; `specs/273-paid-traffic-analytics/legal-basis.md` | `apps/server/tests/unit/test_product_analytics_legal_basis_lifecycle.py::test_every_measurement_level_declares_its_storage_and_its_basis`; `test_product_analytics_launch_approvals.py::test_missing_kinds_are_named_one_by_one` | Без записей об одобрении уровень 3 не подтвержден и не может обрабатывать данные: `assert [state.state for state in states] == [LEGAL_BASIS_CONFIRMED, LEGAL_BASIS_CONFIRMED, LEGAL_BASIS_NOT_CONFIRMED]`; отсутствующие виды одобрения называются по одному: `assert f"approval_missing:{kind}" in gate.blockers`. Частичный пробел: сама запись не зафиксирована |
| FR-048 | покрыто | `legal_basis_lifecycle.py::read_basis_withdrawal_register`, `::level_processing_allowed`, план удаления и обезличивания; `readiness.py` (блокировщик `legal_basis_withdrawn`) | `test_product_analytics_legal_basis_lifecycle.py::test_a_recorded_withdrawal_stops_a_level_even_after_its_approvals`; `apps/server/tests/integration/test_product_analytics_legal_basis_erasure.py::test_level_two_data_is_deleted_and_anonymised_within_the_term`; `::test_level_one_aggregate_is_deleted_within_the_term` | Запись об отпадении основания прекращает обработку: `assert BLOCKER_LEGAL_BASIS_WITHDRAWN in report.blockers`; на реальной базе строки удаляются и обезличиваются: `assert visits == []`, `assert attribute[label] is None`, `assert result.within_deadline is True` |
| FR-049 | покрыто | `advertising_transfer.py::recipient_revocation_trace`, `::revocation_trace_lines`, запрет передачи при отзыве | `apps/server/tests/unit/test_product_analytics_advertising_transfer_gate.py::test_recorded_revocation_stops_the_transfer`; `::test_revocation_trace_reaches_the_recipient_without_personal_data` | Отзыв прекращает передачу: `assert decision.allowed is False`, `assert decision.facts["revocation_delivery_state"] == "confirmed"`; исполнение прослеживается до получателя: `assert trace["delivery_state"] == "confirmed"`, `assert any("revocation recipient=yandex_metrica" in line for line in lines)`, `assert all("graf_pseudo" not in line for line in lines)` |
| FR-050 | покрыто | `retention.py::AnalyticsRetentionRule.__post_init__`, `::validate_retention_rules` (вызов при импорте модуля); `provider_readiness.py` (блокировщики `retention_term_missing`, `retention_category_missing`); `enforce-product-analytics-retention.sh` (`retention_days=missing`) | `apps/server/tests/unit/test_product_analytics_retention_rules.py::test_rule_without_a_term_is_refused`; `::test_unknown_category_is_a_configuration_error_not_keep_forever`; `test_product_analytics_provider_readiness_blockers.py::test_readiness_blocks_when_a_retention_term_is_missing_or_too_short` | Срок `None`, `0` или `-1` отвергается: `with pytest.raises(AnalyticsRetentionConfigurationError)`; готовность блокируется: `assert "retention_term_missing:visit_attribution" in ...["blockers"]`. Оговорка: из-за дефекта FR-036 ветка готова на живом узле все равно блокируется, но по другой причине |
| FR-051 | покрыто | `backup-posthog.sh::fail_backup` (вызов оповещения); `verify-posthog-restore.sh`; `provider_readiness.py` (`BLOCKER_RESTORE_FAILED`) | `test_analytics_retention_enforcement.py::test_backup_fails_closed_and_alerts_when_a_required_class_is_absent`; `::test_restore_verification_detects_a_corrupted_archive`; `test_product_analytics_provider_readiness_blockers.py::test_readiness_blocks_on_a_failed_or_stale_restore_verification` | Неудача копирования вызывает оповещение: `assert (tmp_path / "alert.log").read_text(encoding="utf-8").strip() == "alert invoked"`; неудачная проверка восстановления блокирует заявление: `assert "restore_verification_failed" in ...["blockers"]` |
| FR-052 | покрыто | `backup-posthog.sh` (минимум копий, удаление старых, обязательная внесерверная копия); `infra/posthog/backup.env.example` (`MIN_COPIES=2`, `MIN_OFFSITE_COPIES=1`) | `test_analytics_retention_enforcement.py::test_backup_keeps_two_copies_and_deletes_older_ones_with_a_log`; `::test_backup_requires_an_offsite_destination`; `::test_backup_rejects_a_retention_count_below_the_minimum` | Порядок удаления и минимум проверены: `assert len(remaining) == 3`, `assert "retention_deleted=20260101T023000Z" in result.stdout`; без внесерверного получателя прогон падает: `assert "reason=offsite_command_not_configured" in result.stdout` |
| FR-053 | реализовано без теста | текст: `infra/posthog/backup-restore.md`, раздел «What A Restore Recreates And What Is Lost» — перечислено, что восстанавливается полностью и что утрачивается безвозвратно | `test_analytics_degradation_alerting.py::test_documentation_keeps_the_scope_split_and_the_delivery_deadline` | Единственная проверка — подстрока заголовка: `assert "What A Restore Recreates And What Is Lost" in backup_restore`. Содержание раздела (перечень полностью восстановимого против безвозвратно потерянного) не проверяется ничем |
| FR-054 | покрыто | `infra/scripts/alert-analytics-degradation.sh::build_message` (только коды, области, пороги, метки владельцев); перечень кодов в `infra/posthog/alert-rules.txt` | `test_analytics_degradation_alerting.py::test_alert_delivers_scope_aware_metadata_only_message`; `::test_alert_labels_a_mixed_breach_list_with_both_scopes` | Тест перехватывает тело запроса и проверяет запрет по списку: `for forbidden in ("visitor", "user_id", "account_id", "email", "session_id", "ip_address", "distinct_id"): assert forbidden not in message.lower()`. Токен не попадает ни в сообщение, ни в вывод, ни в файл состояния |
| FR-055 | покрыто | `infra/posthog/alert-rules.txt` (у каждого правила поле `owner_role`); `alert-analytics-degradation.sh` (подстановка имени владельца из окружения, код `alert_owner_unnamed`) | `test_analytics_degradation_alerting.py::test_every_alert_code_has_an_owner_rule`; `::test_guard_state_feeds_the_alert_end_to_end` | Каждое правило и каждый испускаемый код имеют роль владельца: `assert rule.get("owner_role") in RULE_OWNER_ROLES`, `assert code in rules`; имя владельца доходит до сообщения: `assert "analytics-oncall" in message`. Частичный пробел: в репозитории только роли, а случай «владелец не назван» тестом не проверен |
| FR-056 | покрыто | `alert-analytics-degradation.sh --check-channel` (проба `getMe` и `getChat`, локальная запись состояния, journald, дополнительный транспорт); `infra/posthog/graf-analytics-alert-channel-check.service` и `.timer` | `test_analytics_degradation_alerting.py::test_alert_channel_outage_is_detected_independently` | Отсутствие токена обнаруживается без единого исходящего вызова: `assert "alert_channel_result=fail" in missing.stdout`, `assert "alert_channel_reason=bot_token_unset" in missing.stdout`, `assert "alert_channel_independent_detection=journald_and_channel_state_file" in missing.stdout`. Частичный пробел: внешнее уведомление о недоступности канала требует `GRAF_ANALYTICS_ALERT_FALLBACK_URL`, который по умолчанию не задан |
| FR-057 | покрыто | `anonymous_aggregate.py` (`MINIMUM_AGGREGATE_BUCKET_SIZE = 3`, `is_disclosed_bucket`, `reportable_aggregate_criteria`, `select_reportable_aggregate_buckets`); `public/analytics.py::build_public_consent_share_report` | `apps/server/tests/contract/test_public_traffic_measurement_contract.py::test_buckets_below_the_minimum_size_are_not_disclosed` | На реальной базе: два визита не раскрываются (`assert _reportable_buckets(...) == []`), третий раскрывается (`assert reported[0]["visits"] == MINIMUM_AGGREGATE_BUCKET_SIZE`); доля согласия скрыта тем же порогом: `assert suppressed["blocked_reason"] == "below_minimum_bucket_size"` |
| FR-058 | покрыто | `public/analytics.py`; `anonymous_aggregate.py` (синхронная запись агрегата без обращения к внешнему счетчику); маршрут `/analytics/public-event` | `test_public_traffic_measurement_contract.py::test_an_unavailable_provider_leaves_the_page_and_the_count_intact`; `apps/server/tests/browser/public-analytics-consent.test.cjs` (сценарий отказа провайдера) | При недоступном провайдере страница отвечает и счет не искажается: `assert page.status_code == 200`, `assert repeated.status_code == 200`, `assert _stored_download_visits(postgres_seeded_database_url) == 2` при `assert delivery["delivered"] is False` |
| FR-059 | покрыто | `public/analytics.py::normalize_public_analytics_consent` (неизвестное или поврежденное состояние дает запрет); `public/static/public/analytics.js` | `apps/server/tests/contract/test_public_analytics_consent_enforcement.py::test_a_damaged_consent_record_is_read_as_a_denial`; `apps/server/tests/browser/public-analytics-consent.test.cjs` (сценарий поврежденной записи) | По десяти поврежденным записям: `assert normalized["state"] == "unknown"`, `assert normalized["analytics_allowed"] is False`, `assert normalized["behavior_replay_allowed"] is False`; в браузерном прогоне `assert relayCalls(damaged.calls) == 0` |
| FR-060 | документ вместо реализации | только текст: `docs/analytics/product-analytics-posthog-runbook.md`, раздел «Operator Change And Access Revocation Procedure» (отзыв членства, ротация учетных данных, разбор журнала, запись). В коде доступа нет; состояние — `"rbac_audit": "documented"` в `product_analytics/readiness.py` | `test_analytics_degradation_alerting.py::test_documentation_keeps_the_scope_split_and_the_delivery_deadline` — только подстрока заголовка | Тест утверждает лишь наличие заголовка: `assert "Operator Change And Access Revocation Procedure" in runbook`. Механизма отзыва доступа к аналитике (членство, ротация, аудит) в дереве нет |

## Пробелы

### FR-036. Принудительное хранение не работает: скрипт ищет не те таблицы

Вердикт: противоречие.

`infra/scripts/enforce-product-analytics-retention.sh` находит таблицы продуктовой
базы по списку кандидатов (`table_candidates_for`) и проверяет существование
через `SELECT to_regclass('public.<кандидат>') IS NOT NULL`. Фактические имена
таблиц в схеме другие:

| Категория | Кандидаты в скрипте | Реальное имя (миграция и модель) |
| --- | --- | --- |
| `anonymous_aggregate` | `product_analytics_anonymous_aggregate`, `product_analytics_aggregate_buckets`, `anonymous_aggregate`, `product_analytics_aggregate` | `anonymous_page_aggregate_buckets` (`db/migrations/versions/0094_anonymous_page_aggregate.py`, `db/models/product_analytics.py::AnonymousPageAggregateBucket`) |
| `visit_attribution` | `product_analytics_visit_attribution`, `visit_attribution`, `product_analytics_visit_attributions` | `public_visit_attributions` (`db/migrations/versions/0095_public_attribution.py`, `PublicVisitAttribution`) |
| `acquisition_attribute` | `product_analytics_acquisition_attribute`, `product_analytics_client_acquisition_attribute`, `acquisition_attribute`, `customer_acquisition_attribute` | `client_acquisition_attributes` (`0095_public_attribution.py`, `ClientAcquisitionAttribute`) |

Ни один кандидат не совпадает с реальным именем, поэтому на живом узле все три
категории попадут в `missing_categories`, прогон завершится `result=failed` с
кодом `retention_category_missing`, поднимет оповещение и вернет код 1. Следствия:
агрегированные отчеты и атрибуция не удаляются никогда, а заявление о готовности
аналитики блокируется навсегда (блокировщик `retention_category_missing`).

Почему тесты этого не видят:
`test_analytics_retention_enforcement.py` подменяет docker исполняемым файлом,
который отвечает `t` на любой запрос `to_regclass`
(`if "to_regclass" in joined: print("f" if os.environ.get("FAKE_TABLE_MISSING") == "1" else "t")`).
Поэтому `test_retention_execution_deletes_by_age_and_logs_every_deletion`
проходит при любом списке кандидатов, а сверки списка с моделями или миграциями
нет ни в одном тесте. При этом та же фича в других тестах пользуется верными
именами: `test_product_analytics_legal_basis_erasure.py` объявляет
`SERVER_AGGREGATE_TABLE = "anonymous_page_aggregate_buckets"`,
`SERVER_VISIT_TABLE = "public_visit_attributions"`,
`SERVER_ACQUISITION_TABLE = "client_acquisition_attributes"`.

Что сделать, чтобы закрыть:

1. Заменить списки кандидатов на фактические имена таблиц (лучше — брать их из
   метаданных моделей или из миграций, а не дублировать строками).
2. Добавить регрессионный тест, который сверяет имена, используемые скриптом,
   с `Base.metadata` (или с именами из миграций), чтобы расхождение падало в
   тестах, а не в проде.
3. Отдельно проверить, что путь ClickHouse подтверждает именно удаление:
   сейчас скрипт читает `extract(create_table_query, 'TTL[^0-9]*([0-9]+)')`, то
   есть наличие TTL в описании таблицы, а не факт удаления строк.
4. Прогнать `--execute` на стенде и приложить метаданные прогона как
   доказательство.

### FR-037. Два оператора и обязательный второй фактор не реализованы

Вердикт: документ вместо реализации.

Есть только раздел документа `docs/analytics/product-analytics-posthog-runbook.md`.
В коде доступа к аналитике нет: поиск `totp`, `mfa`, `second_factor` по
`apps/server/src/twobrain_rec_server` не находит ничего; в отчете готовности
состояние доступа объявлено константой `"rbac_audit": "documented"`
(`product_analytics/readiness.py`). Единственный «тест» — подстрока заголовка.

Что сделать: либо подключить проверку фактического состояния доступа (число
принятых участников с включенным вторым фактором) к отчету готовности как
блокирующее доказательство, либо честно держать состояние доступа
неподтвержденным до появления записи оператора, а не значением `documented`.
Тест на подстроку заголовка требованием не является.

### FR-038. Версионирование конфигурации и сверка установленного кода с репозиторием отсутствуют

Вердикт: документ вместо реализации.

В коде нет ни версии конфигурации аналитики, ни сверки установленной на сервере
копии скрипта охраны с репозиторием: в `infra/scripts/posthog-runtime-guard.sh`
нет вывода хеша или ревизии, ни один скрипт не сравнивает
`/usr/local/libexec/graf-posthog-runtime-guard.sh` с `infra/scripts/posthog-runtime-guard.sh`.
Единственное упоминание — абзац про периодический обзор в runbook. Тестов нет
вообще: ни один тест в дереве не проверяет FR-038.

Что сделать: добавить режим сверки (например, `--verify-install`, печатающий
sha256 установленной копии и ожидаемый sha256 из репозитория) и тест на него;
ввести версию конфигурации аналитики, попадающую в отчет готовности и в запись
об одобрении.

### FR-039. Нагрузочная проверка не проведена, инструмента нагрузки нет

Вердикт: документ вместо реализации.

Инструмент измерения есть (`infra/scripts/measure-posthog-storage-growth.sh`,
покрыт `test_storage_growth_measurement_reports_the_documented_keys`), но это
измерение роста хранилища, а не нагрузочная проверка: генератора нагрузки в
дереве нет. Ни одного абсолютного объема и ни одной скорости роста не
зафиксировано: таблица в `docs/analytics/product-analytics-capacity-baseline.md`
целиком в состоянии `pending operator receipt`. Факт непроведения зафиксирован
честно: `tasks.md` строка 80 (T076 не отмечена) и
`validation/quickstart-evidence.md`, раздел «Что не проверено», пункт 1.

Что сделать: провести нагрузочную проверку на стенде с живым трафиком, внести
числа в таблицу baseline и заменить `pending operator receipt` на измеренные
значения; без этого требование «перед запуском трафика» не выполнено.

### FR-040. Набора отчетов нет: есть только определения

Вердикт: документ вместо реализации.

`infra/analytics/dashboards/catalog.json`, `posthog/dashboards.json` и
`yandex/reports.json` — это описания, а не отчеты. Сами описания это признают:
`data_availability.status = "not_fillable_today"`, `apply.requires_operator = true`.
Серверный код эти файлы не читает (поиск по `apps/server/src` не находит ссылок
на `catalog.json` и `analytics/dashboards`). Тесты парсят JSON и проверяют
наличие тем, но ни один дашборд не применен и ни один отчет не построен.

Что сделать: применить определения в рабочем пространстве провайдера (шаг
оператора уже описан в `apply.steps`) и приложить запись о применении: имя
дашборда, владелец, состояние, время. После этого FR-040 становится проверяемым
на работающих отчетах, а FR-042 и FR-043 перестают быть обещаниями.

### FR-041. Соединения расхода с конверсиями нет, тест проверяет сам себя

Вердикт: тест без реализации.

В дереве нет ни серверного кода, ни скрипта, который берет расход рекламного
кабинета и делит его на конверсии. Есть раздел `cost_join` в `catalog.json` и
тест `test_product_analytics_report_cost_per_result.py`, который объявляет
собственную функцию `cost_per_result` прямо в файле теста (это признает и
docstring: «Эталонная реализация ниже повторяет правила из
`infra/analytics/dashboards/catalog.json`») и проверяет именно ее. Цитата:
`assert costs == {"brand-search": 2000.0, "generic-search": 7500.0}`. Код
продукта в проверке не участвует.

Что сделать: реализовать соединение (загрузка расхода из выгрузки кабинета,
сопоставление по кампании, расчет стоимости результата, правило «нет данных
вместо нуля») как код продукта или как исполняемый шаг отчета, и перенести
проверки на этот код. Тест, проверяющий собственный эталон, требованием не
является.

### FR-042. Владелец и оговорки объявлены только в определениях

Вердикт: документ вместо реализации.

Проверки `test_every_report_has_an_owner_freshness_and_mandatory_caveats` и
`test_consent_share_caveat_is_required_on_every_report` действительно проверяют
наличие владельца, свежести и обязательных оговорок, включая долю посетителей
без необязательного согласия, но применяются они к записям JSON, а не к отчету.
Отчетов, к которым требование относится, не существует (см. FR-040).

Что сделать: применить дашборды и проверить владельца и оговорки на примененных
отчетах; тогда требование будет подтверждено на том объекте, о котором оно
говорит.

### FR-043. Разделение намерения и активации не видно ни в одном отчете

Вердикт: документ вместо реализации.

Разделение сигналов в данных есть (клик `public_installer_download_clicked`,
факт `public_installer_download_aggregate`, активация
`first_value_session_completed`), и тест
`test_reports_separate_download_intent_from_completed_activation` проверяет
словарь метрик и наличие блока `intent_vs_activation` у двух отчетов. Но
отчета, в котором это разделение видно владельцу, не существует — как и всех
остальных отчетов (см. FR-040).

Что сделать: то же, что для FR-040: применить отчеты и подтвердить разделение
на живом отчете.

### FR-045. Откат на живом сценарии не отработан

Вердикт: документ вместо реализации.

Путь отката реализован как код (`infra/scripts/rollback-product-analytics-providers.sh`,
ветка отката в `posthog-runtime-guard.sh`) и проверен контрактами на явный
метаданный режим: `--metadata-only` возвращает
`rollback_execution=metadata_only_no_state_change`, а операторский hook не
вызывается. Режим `--execute` fail-closed: без явного разрешения и абсолютного
исполняемого `TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK` он возвращает nonzero;
тесты hook не настраивают. Живого прогона не было:
`validation/quickstart-evidence.md` фиксирует
`rollback_status=metadata_only_not_executed` и
`rollback_live_mutation=not_claimed`; запись `rollback` в файле одобрений не
зафиксирована (шлюз `approvals.py` без нее запуск не разрешает).

Что сделать: оператору отдельно провести откат на живом сценарии через
одобренный executor hook (включить измерение, вызвать откат, убедиться, что
измерение выключено, а обычная работа продукта сохранена), записать метаданные
прогона и внести запись `rollback` в файл одобрений. До этого требование не
выполнено, а запуск платного трафика блокируется шлюзом.

### FR-053. Порядок восстановления после потери узла описан, но не проверен

Вердикт: реализовано без теста.

Раздел «What A Restore Recreates And What Is Lost» в
`infra/posthog/backup-restore.md` действительно называет, что восстанавливается
полностью (реляционная база PostHog, данные ClickHouse, объекты записи
сессий) и что утрачивается безвозвратно (события после последнего архива,
незавершенная запись, невыгруженные объекты, классы вне инвентаря, данные
Метрики, уже удаленное сроками хранения). Но единственная проверка — подстрока
заголовка в `test_documentation_keeps_the_scope_split_and_the_delivery_deadline`:
`assert "What A Restore Recreates And What Is Lost" in backup_restore`.
Содержание раздела не проверяется ничем: если перечень потерь из документа
исчезнет, тест останется зеленым.

Что сделать: проверять содержание, а не заголовок: наличие обоих перечней,
упоминание каждого класса хранения из `infra/posthog/backup-volumes.txt` и
явное указание на безвозвратные потери.

### FR-060. Отзыв доступа не реализован

Вердикт: документ вместо реализации.

Есть только раздел «Operator Change And Access Revocation Procedure» в runbook.
Механизма отзыва доступа к аналитике (членство, ротация учетных данных, разбор
журнала) в дереве нет; состояние доступа в отчете готовности — константа
`"rbac_audit": "documented"`. Единственный «тест» — подстрока заголовка:
`assert "Operator Change And Access Revocation Procedure" in runbook`.

Что сделать: зафиксировать доступ как отзываемый проверяемым образом (учет
членства и его изменений, ротация учетных данных, запись об отзыве) и
подключить это к отчету готовности. Подстрока заголовка требованием не является.

## Частичные пробелы у требований с вердиктом «покрыто»

Эти требования получили вердикт «покрыто»: механизм есть и тест проверяет
именно его. Ниже — то, что осталось незакрытым внутри них и что не позволяет
считать требование закрытым на живом узле.

- **FR-030.** Внешняя доставка оповещения проверена на подставном `curl`.
  Живого срабатывания не наблюдалось: `validation/quickstart-evidence.md`,
  раздел «Что не проверено», пункт 4. Учения `--drill` на живом канале и записи
  о них нет.
- **FR-031.** Проверка статическая: тесты читают текст скрипта охраны. Живого
  всплеска трафика на сайт не создавалось (там же, пункт 5).
- **FR-033.** Конкретное целевое хранилище не названо: в
  `infra/posthog/backup.env.example` строка `GRAF_POSTHOG_OFFSITE_COMMAND=`
  пуста, метка по умолчанию — `operator_offsite_target`. Фактическая выгрузка
  за пределы узла не производилась (там же, пункт 11). Требование говорит о
  «названном целевом хранилище», а имя появляется только из окружения
  оператора.
- **FR-034.** Ветка `backup_missing` (файл состояния есть, но успешного прогона
  в нем нет) не покрыта ни одним тестом: проверены `backup_state_unavailable`,
  `backup_stale`, `backup_copy_count_below_minimum`, `backup_offsite_copy_missing`.
- **FR-035.** Свежесть и факт проверки восстановления на продуктивном стенде не
  измерялись: контрактные тесты работают на подставных хостах и каталогах
  (там же, пункт 6).
- **FR-046.** Локальная проверка согласованности теперь проходит для
  repository docs: `test_every_published_document_names_the_runtime_revision`
  подтверждает точную редакцию `2026-09-15.1` в каждой копии, а
  `test_a_stale_published_document_is_not_masked_by_another_document` и
  `test_a_missing_published_document_is_not_replaced_by_combined_text` проверяют
  расхождения по отдельному пути. Внешние публикации, настройки провайдера и
  подключение проверки к выпускному шлюзу остаются операторскими границами и не
  заявляются закрытыми этим локальным изменением.
- **FR-047.** Записи об одобрении не зафиксированы
  (`validation/quickstart-evidence.md`, пункт 10). Шлюз работает и без них
  запуск не разрешает, но само подтверждение остается действием владельца.
- **FR-050.** Термин и его отсутствие обрабатываются верно, но из-за дефекта
  FR-036 продуктовая ветка принудительного удаления не находит таблицы, поэтому
  готовность блокируется блокировщиком `retention_category_missing` постоянно, а
  не только при отсутствии срока.
- **FR-055.** В репозитории лежат роли, а не имена
  (`infra/posthog/alert-rules.txt`: `owner_role=infra_operator` и подобные);
  имя владельца подставляется из окружения. Случай «владелец не назван» код
  обрабатывает (`alert_owner_unnamed`), но теста на этот случай нет: оба
  упоминания кода в тестах — отрицательные утверждения
  (`assert "alert_owner_unnamed" not in result.stdout`). Назначение владельцев в
  продуктиве остается записью оператора.
- **FR-056.** Обнаружение недоступности канала не зависит от самого канала
  (локальный таймер, файл состояния, journald), но внешнее уведомление об этом
  требует настроенного `GRAF_ANALYTICS_ALERT_FALLBACK_URL`; по умолчанию он
  пуст, и без него обнаружение остается видимым только в journald и файле
  состояния.

## Самое важное

T093 устраняет прежний пробел FR-046 для repository docs: точная редакция
`2026-09-15.1` теперь есть в каждой проверяемой копии, а проверка не сводит их в
один текст. Внешние публикации, сроки хранения провайдера и другие операторские
условия по-прежнему требуют отдельного подтверждения и не считаются закрытыми
этим локальным изменением.

Что действительно мешает запуску платного трафика:

1. **Сроки хранения не применяются к агрегатам и атрибуции (FR-036).** Скрипт
   принудительного удаления ищет таблицы, которых нет, поэтому агрегированные
   отчеты не удаляются, а готовность аналитики блокируется навсегда. Дефект
   спрятан подставным docker в тесте, который отвечает `t` на любой запрос о
   существовании таблицы.
2. **Отчетности нет (FR-040, FR-041, FR-042, FR-043).** Все четыре требования
   закрыты определениями JSON, ни один дашборд не применен, данные объявлены
   `not_fillable_today`, а стоимость результата вообще не имеет кода: тест
   проверяет собственную эталонную функцию. Запускать платный трафик, не имея
   ни одного работающего отчета, значит платить без возможности прочитать
   результат.
3. **Доступ не управляется (FR-037, FR-038, FR-060).** Второй оператор,
   обязательный второй фактор, версионирование конфигурации, сверка
   установленного кода охраны с репозиторием и отзыв доступа существуют только
   текстом; в коде состояние доступа — константа `documented`. При смене состава
   операторов отзывать нечего, потому что выдавать доступ средствами GRAF
   нечем.
4. **Путь отката не отработан (FR-045), а проверка согласованности текстов
   согласия не проходит и ничего не блокирует (FR-046).** Оба пункта — прямые
   условия снятия блокировки платного запуска в самой спецификации; шлюз
   одобрений без записи `rollback` запуск не разрешит, и это единственное, что
   сейчас удерживает ситуацию.
5. **Нагрузочная проверка не проведена (FR-039).** Ни абсолютного объема
   хранилища, ни скорости роста не зафиксировано: таблица baseline целиком в
   состоянии `pending operator receipt`.
