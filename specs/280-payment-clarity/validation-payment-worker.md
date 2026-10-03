# F280 / T030 — проверка причинного исправления фоновой оплаты

Дата: 3 октября 2026. Lane: high-risk-product / active Spec Kit slice.
База рабочего checkout: `6dbbe450876e7b7dbdacfc3ce542322eaaff6e3c`; изменения еще не закоммичены/не выпущены.
Scope: только регистрация существующего reconciliation worker, проверка фактической БД роли и связанные тесты. Автор не менял reviewer checklist, задачи, маршрут/шаблоны/JavaScript других исполнителей, GitHub или production.

## Подтвержденная причина

До изменения read-only диагностика показала один счет на10₽ после выпуска2.7: YooKassa GET `succeeded`, `paid=true`, `test=false`, сумма/metadata совпали, receipt registration `succeeded`. В GRAF invoice pending/operation provider_pending, grant0, matching webhook pending_reconciliation. Связь с конкретным пользователем не устанавливалась. В одинаковом maintenance context processing/app роль видела0pending событий, maintenance роль1. Шесть Temporal reconciliation workflows за30мин завершились COMPLETED с processed0 без ошибок. Это ошибка места выполнения при штатно действующем RLS, а не доказательство недоступности провайдера. Идентификаторы/контакты/карты/секреты не записаны.

## RED до production edit

1. Только новые тесты, старая реализация:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_rls.py -k reconciliation_activity
```

Итог: **1failed/1passed/11deselected**,4.17сpytest,8сphase. `test_reconciliation_activity_rejects_real_app_role_before_empty_success` дал **DID NOT RAISE RuntimeError**: настоящий `session_user=twobrain_rec_app`, правильный maintenance context и существующий pending webhook, но activity вернула успешный пустой результат. Контрольный maintenance/replay сценарий уже passed, доказывая штатную финансовую логику. Лог: `/tmp/graf-f280-payment-worker-causal-red.log`. Изолированный PostgreSQL контейнер удален.

2. Registry contract на старом processing worker: **1failed/3passed**,0.17с; reconciliation workflow еще зарегистрирован в processing. Лог: `/tmp/graf-f280-payment-worker-registry-red.log`.

Первый подготовительный SQL запуск до причинного RED упал на отсутствующем synthetic provider secret в Settings fixture (2failed); исправлена только fixture. Это не причинный RED. Лог: `/tmp/graf-f280-payment-worker-red.log`; cleanup выполнен.

## Реализация и границы

- Processing worker больше не опрашивает payment reconciliation queue; renewal и остальные workflows не переносились.
- Maintenance worker обслуживает **прежнюю** очередь, workflow/activity names и payload. `billing_reconciliation_workflow.py` побайтно совпадает с HEAD: очередь, IDs, тело workflow,300сcadence и retry не изменены. Старые histories не переписываются, alias/new queue нет. Выпуск должен сначала прекратить прежний processing poller, затем maintenance обслужит ту же очередь.
- Проверка БД выполняется перед запуском службы, при каждом новом Temporal соединении до poller, а также внутри activity после context и перед чтением. Проверяются настоящий session_user/current_user, row_security=on, отсутствие superuser/BYPASSRLS, действующий rec_maintenance_allowed и точный operation/feature context. URL hints недостаточны. Ошибка статическая, без данных соединения.
- Startup probe READ ONLY, с закрытием сессии и dispose engine. Ошибочная роль не дает успешный0.
- Повторное подключение создает свежую wrapper activity; старый poller и зависимые циклы полностью остановлены до закрытия клиента и нового подключения. Как исключение, так и неожиданное обычное завершение poller запускают cleanup/reconnect.
- Ни RLS, ни права processing, ни транзакции выдачи прав/штатные provider identity checks не расширялись. В тестах provider synthetic GET-only; create payment assertion не вызывался.

## Окончательный GREEN

```sh
cd apps/server
uv run --extra dev --extra evaluation pytest tests/contract/test_billing_reconciliation_workflow.py tests/unit/test_billing_reconciliation_activity.py tests/unit/test_maintenance_worker.py -q
```

**25passed**; лог `/tmp/graf-f280-payment-worker-unit-final-green.log`. Проверены registry names/queue/actual wrapper delegation, обязательная identity проверка до maintenance, unsafe role/current role/row_security/superuser/BYPASSRLS/context denial, не-PostgreSQL отказ, startup refusal до любых loops/poller, сохранение calendar при Temporal outage, cleanup при cancel/error/normal return, повторное подключение без двух pollers, role refusal после подключения с закрытием клиента.

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_rls.py tests/integration/test_billing_stuck_operation_recovery.py
```

**19passed**; лог `/tmp/graf-f280-payment-worker-postgres-final-green.log`. Настоящие PostgreSQL app/maintenance роли, фактический session_user и действующие RLS policies. App activity явно отказывает до provider GET и без изменений invoice/webhook/grants. Maintenance видит событие, применяет подтвержденный10₽ к personal subscription и одному grant. Повторный durable signal делает второй GET, но сохраняет тот же paid_through,1grant/1invoice/1operation; create0. Отдельный startup verifier на настоящей app роли отказывает, на maintenance проходит. Existing финансовая/межпространственная изоляция и stuck operation recovery сохранены. Cleanup: isolated_container_removed.

До добавления последних startup/normal-return/reconnect-denial сценариев промежуточные GREEN были23unit/18SQL; окончательные результаты выше относятся к текущему коду. Ruff для всех7принадлежащих файлов — PASS. `git diff --check` — PASS.

## Дайджесты проверенных файлов

| Файл | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/database.py` | `b75f7a35952b8725ac1017e926ddea3449f480c71de0d6b3a7f83ae49fe6197f` |
| `apps/server/src/twobrain_rec_server/workflows/worker.py` | `c6a33d8f920ca5032e0b45cb0b433fcb85a398cde76c3f5fa043a35a43a599d6` |
| `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py` | `f79ba3c4ebfbed53718883c523a87877fd7a0ab0071a5cd0b9da618890fc9a1b` |
| `apps/server/tests/contract/test_billing_reconciliation_workflow.py` | `b6a779b9b74f66a45a663068feef53434176e9c6e1d1d4f901bb979b341c8d40` |
| `apps/server/tests/unit/test_billing_reconciliation_activity.py` | `f32b65c4ac7c20f8a002314349597e558db270adc2aa374a6a5ebc9945d15ed8` |
| `apps/server/tests/unit/test_maintenance_worker.py` | `ba9a1644d4535de09b81f13f001a720cff0b2d217962f03fc794a577fcac8dcb` |
| `apps/server/tests/integration/test_billing_rls.py` | `34e46cebb34cdd819542772154253b86b2d3b6c20066566bf6e473a5e888efa5` |

## Следующие gate

T030 implementation ready для независимого обзора; задачи/issue не закрывались исполнителем. Необходимо независимое review/converge и общий exact-SHA PR/Full/CD выпуск. После выпуска readonly проверка должна подтвердить применение **того же** настоящего succeeded платежа, доступ и остановку старого poller; synthetic GREEN не заменяет live readback. T011/T012/F278, банк/возврат/recurring и человеческая конверсия этим отчетом не закрываются.
