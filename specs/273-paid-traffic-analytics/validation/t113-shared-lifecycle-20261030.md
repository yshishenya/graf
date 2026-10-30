# F273/T113: единая проверка обязательных локальных удалений

30.10.2026, ветка `codex/f273-local-period-20261029`, основа
`8350b688788861d8b35dd304bcf325f7eef305e8`, T113/#7804.
Lane `high-risk-product`, существующий Spec Kit; Legacy Impact `untouched`.
До кода [независимый проектный гейт](t113-shared-lifecycle-design-review-20261030.md)
дал117/0, CRITICAL0/HIGH0. Неизменные требования сверены по хешам по принятому
исключению F273; применимые разделы полного алгоритма и зависимости перечитаны.

## Изменение

Тело прежнего `_backup_lifecycle` перенесено в `_local_lifecycle` без изменения
SQL, политик, охвата четырёх категорий, сроков, RLS или digest. Ядро принимает
непустые неизменяемые bytes до10МБ и само открывает read-only RR на удержанной
reduced source. Backup wrapper сохраняет private_bytes/0700/0600/10МБ,
повторно читает файл после закрытия transaction и возвращает прежнюю пару.

Runtime получает actual legal bytes из прежнего удержанного binding, отдельно
сравнивает bytes всех writers и сохраняет прежнюю сверку digests. Bytes остаются
в памяти, не входят в proofs/вывод. Обязательный register_raw передаётся в
_runtime_databases; ядро вызывается на той же физической reduced source с
root=snapshot до/после yield, каждый раз в новой RR. Proof содержит только
lifecycle_sha256. Наружный operations context после закрытия DB повторяет
прежние file/proc/identity/freshness проверки.

Accepted category даже при пустой таблице запрещает успех; accepted
account_closure сохраняет прежний смысл: нужны реальные completed/purge,
хронология, точный охват и отсутствие остатков. Исторические сроки остаются
unverified, provider deletion этим reader не подтверждается.

## Проверки

До source изменений расширенные unit дали2FAIL/1PASS на отсутствии register_raw.
Native RED дал2FAIL: отсутствовали обязательный вход runtime и общее ядро;
собственный контейнер удалён. После source изменения выполнен профиль:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q --tb=short \
  tests/unit/test_activation_operator.py \
  tests/unit/test_activation_restore_replay.py \
  tests/integration/test_activation_product_drain.py::test_native_runtime_database_preflight_full_schema \
  tests/integration/test_activation_restore_replay.py::test_source_lifecycle_proves_absence_without_hidden_rls_rows \
  'tests/integration/test_activation_restore_replay.py::test_coherent_copy_is_native_and_can_be_restored[success]' \
  tests/integration/test_activation_restore_replay.py::test_all_four_categories_replay_and_source_postconditions \
  tests/integration/test_activation_restore_replay.py::test_old_copy_replays_only_exact_account_and_quarantines_both \
  tests/integration/test_activation_restore_replay.py::test_category_case_erases_ledger_and_preserves_other_relations
```

**358 PASS/37 Linux SKIP/2 warnings,179,62с**, collection395, digest
`38e30454eccdd3fc36eeb941f7e7eb4c2cb272c16504d47e40c97d6907291d35`.
Полный профиль включает настоящий PG17, backup/restore, роли/RLS/catalog/access,
непустые closure/purge/four-category/replay и owned cleanup. Все ресурсы runner
удалены. Предупреждения прежние pytest import rewrite и Starlette/httpx.

Native runtime cases проверяют valid v2, неверную версию/формат/непокрытый
withdrawal, accepted/failed category, applied с остатками и без них, unresolved
closure, изменение таблицы/closure metadata после yield. Отсутствующий keyword
запрещён. Source test проверяет None/str/пустые/oversize bytes и равенство
wrapper/core на непустом наборе, в том числе closedDB false/limit0 без
reconnect reduced source; metadata восстанавливается в finally.

После полного профиля усилен только cancellation case в native runtime тесте:
при входе в настоящий core другое собственное соединение удерживает table
lock; pg_stat_activity/pg_blocking_pids подтверждают PID, application_name,
Lock и первые128символов настоящего CLOSURE_POLICY_QUERY. Две отмены прерывают
именно этот запрос внутри read-only RR; все owned соединения закрыты, чужой
учебный lock освобождён в finally. Исходный pg_sleep перед core не принят
за это доказательство. Конечные cancel_lifecycle/good/lifecycle_closure_changed:
**3PASS/2warnings,14,71с**, cleanup PASS. Продуктовый source, unit и source/replay
тесты после полного профиля не менялись; хеши полного профиля сохранены отдельно.

Linux actual bound files/settings/runtime: **106PASS/0SKIP,0,61с** на прежнем
Python3.13 образе `sha256:37d27de327e5876b4c890a7e6c3dd98ab8fd89476180d6deb42d262411c1ccbe`.
Read-only source, без сети/socket/приложения, одноразовый volume с ACL и
`docker run --rm`; временные pure-Python pytest modules удалены штатным
TemporaryDirectory. Новых зависимостей проекта и образов нет. Проверено
actual bytes, отказы bound-file и raw mismatch при одинаковом digest;
public result не содержит synthetic register sentinel. Mac skips отдельно.

Неуспешные уточнения тестовой среды сохранены: первый контейнер без stdin
ничего не проверил и не принят; tmpfs не поддержал ACL (103PASS/3FAIL),
volume дал полный PASS. Source closedDB test первоначально пытался менять
ALLOW_CONNECTIONS из текущей DB (22PASS/1FAIL), исправлен на административное
соединение postgres. Lock до core блокировал более ранний catalog; затем
отслеживался неверный SQL prefix; при правке import был один collection error.
Эти попытки не выданы за успешные. Конечное наблюдение отмены причинное.

Ruff/governance/development-process/fragments/whitespace и локальные ссылки
проверяются перед frozen inventory и независимым code review. Журналы, runner
и контрольные суммы остаются ignored в `.dev/growth/t113-shared-lifecycle-*`.

## Остаток

Это общий source reader, не единый graf-local receipt и не полный допуск.
Installed jobs/guard/purge/cron, shell graf-local, полный preflight, верхние
initial/backup/verify/actual-restore/resume, CD/rollback/daily, T112/T113/#7804
и AC01–AC06 открыты. `full_preflight_not_implemented` и
`activation_recovery_unverified` сохранены. Рабочих T0/ready, включения
аналитики/IP/получателей, выпуска, Dev или новых публикаций не было.
Трафик и продажи этими техническими проверками не доказаны.
