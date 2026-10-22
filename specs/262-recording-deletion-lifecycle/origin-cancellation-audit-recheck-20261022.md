# F262 / T008 / #6883: аудит отмены до создания встречи

Дата: 2026-10-22. База: `9b286f6d9df01f4b948d7db1673aff99c78635ff`.
Ветка: `codex/262-origin-cancellation-audit`.
Область: active Spec Kit slice, high-risk deletion/audit.

## Обнаруженный пробел и исправление

Core guard/миграция уже подтверждены, но первоначальная origin-only отмена
не сохраняла устройство. Это противоречило data-model.md, разделу
RecordingOriginCancellation, и PRD §26. Исходный отрицательный тест на
неизменённом продуктовом коде завершился `assert 0 == 1`: нет связанного
события. Историческое отсутствие аудита не выдаётся за утраченный CI.

Использован существующий MeetingLifecycleAuditEvent без миграции:
recording_origin_canceled, accepted, фиксированная причина; workspace,
исполнитель и устройство из TenantScope; время из accepted_at marker.
Оба необязательных FK пустые; metadata содержит только серверный
cancellation_id. Builder принимает для него только UUID, затем возвращает
каноническую строку; строки, включая UUID-строки, None, bool/числа и
структуры отклоняются. Прежние запреты приватных metadata сохранены.

Marker и audit записываются под общей origin-блокировкой и в одной
транзакции; commit остаётся в HTTP endpoint до ответа. Повтор не создаёт
новое событие и не меняет первое устройство. Старые markers без аудита
остаются действительными без вымышленного заполнения истории.

## Доказательства локальной проверки

Все данные синтетические, PostgreSQL из штатного isolated runner.

| Проверка | Результат | SHA-256 журнала |
|---|---|---|
| Исходный RED, origin-only scope acceptance | 1 ожидаемый FAIL: audit отсутствует | df6e1fe6ff9fa77802533413ef5ed00f4b738b1764fa3e1bcd9d68c06e84d50b |
| Девять тематических файлов после исправления | 60 PASS / 0 FAIL / 0 SKIP, 56.55 с pytest | f1177436eab6d9a2c98fd880e8495492822e1ff6b1b71f5e96d8d1e0491ebed6 |
| Три дополнительных отказа устройства | 3 PASS / 0 FAIL / 0 SKIP, 4.52 с pytest | 176d60f81eaf83dc22cffbac93f8a8f700b1f9f91233a408be89effec9df9959 |

Итого **63 разных случая**, без повторного прибавления прежних запусков.
В каждом запуске два прежних предупреждения pytest/Starlette; ошибок и
пропусков нет. Все три изолированных контейнера штатно удалены.

Основная команда:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_recording_origin_cancellation.py \
  tests/integration/test_recording_deletion_scope_acceptance.py \
  tests/integration/test_recording_deletion_migration.py \
  tests/unit/test_deletion_audit_metadata.py \
  tests/integration/test_cabinet_hx_delete_feedback.py \
  tests/integration/test_deletion_lifecycle_blocks_access.py \
  tests/integration/test_local_purge_coordination.py \
  tests/integration/test_recording_sync_conflicts.py \
  tests/integration/test_recording_workflow_deletion_races.py
```

После добавления отрицательных сценариев отдельно выполнен
`test_recording_origin_cancellation.py::test_unavailable_session_device_cannot_create_cancellation_or_audit`:
отозванное, pending и устройство другого workspace получают 403 без
marker/audit/receipt. Это три дополнительных ID, отсутствовавшие в наборе60.

Проверены после commit/re-read: точные actor/device/workspace/receipt/time,
NULL FK и отсутствие фиктивных Meeting/DeletionRequest/PurgeTask; повтор
двумя настоящими AuthSession с разными RegisteredDevice одного владельца;
конкурентные отмены с одним marker/audit; ошибка SQLAlchemy before_insert
с rollback обоих объектов и последующим успешным create; старый marker
без выдуманного аудита. Restricted PostgreSQL role выполняет INSERT аудита
и marker; чужой workspace их не видит. Owner-only RLS относится к marker:
общий lifecycle audit намеренно доступен в своём workspace по его политике.
Сохранены оба порядка create/cancel и namespace, guard обоих create callers,
три миграционных теста и пять серверных файлов quickstart.

Ruff пяти изменённых Python-файлов, compileall двух source-файлов,
diff whitespace, check_spec_kit_governance, check-development-process,
validate-changelog-fragments и validate-legacy-impact — PASS.

## Review и узкая сходимость

Requirements review: CRITICAL0/HIGH0, requirements10/0, security-ux10/0;
основания в review-t008-audit-checklists-20261022.md. Scoped analyze не
обнаружил противоречий FR-008/009/014/019/021, US3/AC3, S06/S10–S12/S26/S27/S50
и существующей T008. Полная матрица22FR/7SC→23tasks сохранена в analysis.md.

Независимое ревью кода: PASS, CRITICAL0/HIGH0, все шесть условий
выполнены; report review-t008-audit-code-20261022.md прочитан основным
агентом, все приведённые контрольные суммы проверены. Узкая сходимость
T008: новых обязательных доработок нет, tasks.md сохранён без изменений.
До новых exact-SHA/base GitHub checks и слияния issue остаётся открытой.

## Границы

Приёмка относится только к T008. T009/#6884, установленная приёмка всей F262,
S01–S51 как полный сквозной набор, выпуск и production этим отчётом не
закрываются. Исторические квитанции не переписаны. Для слияния обязательны
новые governance-fast, macos-pr и pr-metadata с проверкой общего валидатора;
для закрытия — merged PR и prospective/actual live closeout. Выпуск требует
отдельного frozen candidate/release-full. GRAF Dev не заменялся.

Legacy Impact: untouched; нет нового legacy alias/fallback/flag/dependency.
Существующие исторические markers сохраняются без нового пути совместимости.
