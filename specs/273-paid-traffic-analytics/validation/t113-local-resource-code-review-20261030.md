# F273/T113: независимая проверка реализации локального ресурсного пути

30.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`dc8b0cd055bccbc73cf5dbdf6302f88225c4f8bc`, T113/#7804.
Путь `high-risk-product`, действующий Spec Kit. Проверен незакоммиченный diff
и его зависимости; рабочий сервер не проверялся.

## Решение

**SCOPED CODE REVIEW PASS. Открытых замечаний P1:0, P2:0.**
Реализация соответствует принятому ограниченному проекту. Все117 вопросов
контрольных списков перечитаны; **117 checked / 0 unchecked**, отметки не менялись.
Этот PASS допускает дальнейшие штатные проверки/сохранение среза, но не открывает
рабочее измерение, выпуск, T113 или коммерческую приёмку.

Точные проектные источники:

- precode SHA-256 `33a72287327881b59b6a8b2bd11c1546d112442aaa8eaac29906b9484728e369`;
- [проектное ревью](t113-local-resource-design-review-20261030.md), SHA-256
  `d37322184f66d5efb73db7762364d66dde0d3eee7aca6aac6ed8370ae295886f`;
- [отчёт исполнителя](t113-local-resource-20261030.md), SHA-256
  `19ec00e88a13306bceaa732d313cdab17827d414466c0dd01d2e259cda19d25c`.

Независимо сверены **23/23** записей source inventory
`.dev/growth/t113-local-resource-inventory-20261030.json`, SHA-256
`92c4efc568630ea747aec33cf534797162bc2d8a84de1455604f0cad76287854`.
Таблица ниже сохраняет этот состав в Git. Собственный отчёт в inventory
не включён во избежание круговой контрольной суммы.

## Проверка фактического пути

Прочитан весь diff collector → capacity → guard → alert → provider/local
consumers, все изменения tests/fixtures/docs/fragment/growth plan и применимые
полные функции/разделы. Дополнительно проверены прежние atomic writer,
allocated traversal, GRAF relation metadata, growth, protection transitions,
runtime environment parser, ancestry/identity helpers и coherent backup.
Уточнение lexical canonical override и расширение scope-матрицы тестов,
поступившие в ходе проверки, перечитаны по конечному diff.

1. **Обнаружение и объём.** `runtime_roots` использует `--no-trunc`, полные
   уникальные64hex IDs, точный inspect набор и labels. Local отсутствие
   контейнеров не обходит оба volume lists. Mounted/prefix/labelled/detached
   volumes классифицируются, Name/mountpoint сверяются. Неполнота/неизвестность
   не превращается в отсутствие. Default posthog сохраняет обязательные
   runtime/classes. Прежние allocated blocks/непересекающиеся классы и
   metadata-only GRAF relations не заменены полным разбором продуктовой БД.
2. **Архивы и файловые ресурсы.** Выделенные аналитические архивы продолжают
   считаться целиком. Local ENOENT допускается лишь для leaf при существующих
   безопасных directory ancestors; links, PermissionError и missing parent
   дают неполноту. Mixed GRAF backup parent фиксирован независимо от app path.
   Canonical прямой override ребёнок без links и отдельного устройства
   проверяется collector и actual runtime. Отсутствующий parent не создаётся
   guard. Coherent helper отвергает иной parent. Runtime digest включает
   ancestry/parent/override identity, повторная проверка обнаруживает замену.
3. **Граница смешанных копий.** Неизвестная аналитическая доля полного GRAF
   backup не приписывается нулю или точным analytics bytes. Parent входит в
   analytics-role filesystem reserve, physical resources дедуплицируются.
   Неполный ввод не стирает независимо известный свежий низкий запас. Точные
   20%/10%,128GiB и deadline21.11.2026UTC прежние. Отдельные staging mounts,
   installed jobs/cron и оценка места для двух копий/restore не объявлены
   выполненными этим collector; это сохранённый HOLD полного оператора.
4. **Область и версии.** Sample/alert требуют version3 и scope. Scope входит
   в inventory; смена делает старый growth anchor несопоставимым и требует
   согласованного budget/config. Capacity не принимает старый/чужой sample.
   Guard передаёт explicit scope каждому collector/capacity/protection вызову.
   Неверный guard scope отвергается до mkdir/probes. API ожидает scope из
   проверенного пути, а не из переменной guard: provider явно posthog,
   `_runtime_operations` явно graf-local после local_only Settings.
5. **Пробы и оповещение.** Local не вызывает PostHog health/ClickHouse/queue/
   container health probes и после24ч не вызывает event_count. Provider-only
   показатели выводятся not_applicable. Product ready/host sensors и общий
   capacity/latch остаются. Alert принимает только новую известную область,
   выводит безопасный literal или unknown, сохраняет отдельные backup/retention
   проверки и не предоставляет разрешение на запись.
6. **Инцидент и восстановление.** Protection version2 обязана иметь тот же
   scope; lstat отличает реальное отсутствие от link/необычного объекта.
   Старый/повреждённый/чужой state не перезаписывается и не создаёт observed.
   Даже observed нельзя автоматически перенести в другой scope. Restore
   сначала валидирует существующий incident, затем receipt version2 со scope,
   sample/budget/config/incident/times/growth и actual Config.Env hash.
   Общие proofs остаются, provider proofs заменяются local review лишь для
   исходного graf-local incident. Lock, durable request, один успешный переход,
   retry после ошибки, auto-off/dryrun/apply_failed и запрет timer restore
   сохранены. Переход рабочего state1 намеренно не реализован и остаётся HOLD.
7. **Документы и границы.** Operations, capacity baseline, runbook и provider
   rollback согласованно описывают версии, scope и ручное восстановление.
   Plan/tasks/quickstart и growth plan не закрывают T113/T116/T097 или трафик/
   продажи. Изменений SQL, миграций, платежей, прав, endpoints и новых служб нет.
   Integration fixture только привязывает существующий synthetic backup parent.

## Доказательства проверок

Журналы прочитаны, конечные контрольные суммы сверены. Проверяющий сам не
запускал тесты, Docker или БД; результаты исполнения принадлежат исполнителю.
Профили пересекаются и не суммируются.

| Проверка | Результат | Прочитанный артефакт |
| --- | --- | --- |
| Причинный RED до source | 4FAIL: отсутствуют scope arguments | `t113-local-resource-red-20261030.log` |
| Конечные оба contracts целиком и unit operator | **557PASS / 104LinuxSKIP**,188.15с | `t113-local-resource-frozen-20261030.log` |
| Readiness consumers | **21PASS** | `t113-local-resource-readiness-20261030.log` |
| Linux actual file/settings/runtime cases | **175PASS / 0SKIP**, exit0 | `t113-local-resource-linux-final-20261030.json` |
| Конечный Linux resource profile | **41PASS / 0SKIP**, exit0 | `t113-local-resource-native-final-20261030.json` |
| Scope matrix retry/once/dryrun/auto-off/applyfail/parallel | **14PASS** | `t113-local-resource-modes-20261030.log` |
| Local links | 182, missing0 | `t113-local-resource-links-20261030.json` |

Все названные сырые журналы находятся в ignored `.dev/growth/`.
SHA-256 конечного общего журнала
`8d873ed48b5fb2826f61d61e8e8af90c769f019ab3efe7a4e88e829befd50fd0`;
Linux runtime JSON
`7f663616250082bc72df84ee308e0aeb5f38b12ae6fbc017a1382e05bdada513`;
Linux resource JSON
`8107137f2346612c69f2c5d7e6e84f49dd0cea1b16eead7ca7ec653509a91d99`.

Оба Linux JSON указывают exit0, execution_verified=true, network=none,
read-only source/deps и временные зависимости; тестовые SHA совпадают с
текущими файлами. Прочитан runner resource profile: pytest действительно
выбирает новые проверки, есть непустой executed count, отсутствие skips
проверяется; Docker socket не монтируется, контейнер --rm. Root runtime
профиль отдельно покрывает Linux cases, пропущенные на Mac. Это изолированные
проверки, не доказательство установки или работы production guard.

Из предыдущих2FAIL полного contracts прогона не сделан ложный PASS: проверена
правка устаревших synthetic Docker IDs/labels и последующий полный557PASS.
Прежние warnings pytest/Starlette и config warning Linux описаны в отчёте;
ошибок последнего прогона нет. Ruff, bash syntax, governance, process,
fragment и whitespace исполнитель указал как PASS; проверяющий не приписывает
себе их запуск. Полный native PG профиль не запускался, SQL не менялся;
его прежнее доказательство не переносится на новые байты.

## Повторное чтение117 вопросов

| Checklist | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements.md | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement.md | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security.md | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra.md | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | **117** | **0** | Все вопросы перечитаны, отметки не изменены. |

Применимые требования/зависимости перечитаны, неизменные крупные baseline
переиспользованы по разрешённому исключению F273 и сверенным хешам из
проектного ревью. Изменённые нормативные разделы прочитаны полностью.
Новых нарушений конституции и требований в рассмотренном срезе не найдено.

## Сохранённые ограничения

`full_preflight_not_implemented` и `activation_recovery_unverified` остаются.
Не приняты полный installed jobs/cron/purge/retention/staging, рабочий переход
protection v1, верхний initial/backup/verify/actual restore/resume и оценка
места для новых копий, CD/rollback/daily, рабочие ready/T0/IP/получатели,
exact-SHA CI/Full/release, T112/T113/#7804 и коммерческие AC01–AC06.

Рабочие наблюдения о17,94% свободного места и установленном старом timer
принадлежат отчёту исполнителя; в этом независимом ревью повторно не проверялись.
PASS кода не разрешает обойти20% reserve, удалить данные/образы/архивы или
включить writer. Изменений рабочих данных проверяющий не делал.

Изменён только этот отчёт. SSH, Docker, БД, Dev, тесты, Git/GitHub mutations,
публикации и выпуск проверяющий не выполнял. Следующая стадия — штатные
проверки точной версии и сохранение среза при продолжающихся общих HOLD.

## Полный проверенный inventory

| Путь | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `16fe8c3e5a6e57642572d28755e0c89164be3f577636b007f3180ca0f68e9421` |
| `apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py` | `6b83d5c7ceccbc92262c50a95297de96bd65d3ddbe32d028588b39e90c6445dd` |
| `apps/server/tests/contract/test_analytics_degradation_alerting.py` | `a2e48b9f8a8b310fcb1554490a182b866733732c6bc32ebf6507973424631840` |
| `apps/server/tests/contract/test_analytics_retention_enforcement.py` | `83379816a617e3e4ea964f94072c3f16ba7a0d5ad90bbdfe9fc07aeec696538c` |
| `apps/server/tests/fixtures/analytics_operations.py` | `1076eabbab1cfc6fbc13995338f7ea88e669607a7f553b605c01f4492d3774f8` |
| `apps/server/tests/integration/test_activation_restore_replay.py` | `24b512a94f85976bd1fdf77096a88f94657006302b1698e3016ba317eea27b7f` |
| `apps/server/tests/unit/test_activation_operator.py` | `43388a165fec93161828a81fef4006a15ddc9b56db1b8ff29d630cc6b076d4c5` |
| `changes/unreleased/F273.yaml` | `01411465d3fb4dee6cbd95b0048866feb59928fa74fa949373edc593202cfe38` |
| `docs/analytics/product-analytics-capacity-baseline.md` | `c1cd0f6a6edbb7773ec7060bb305b69fe5c54032ac14548b715628dd0f6bc536` |
| `docs/analytics/product-analytics-posthog-runbook.md` | `abf8cf67b40136e309ccf33c0f4a555b4e2dbf876c42605fd021a663c6376933` |
| `docs/analytics/product-analytics-provider-rollback.md` | `178b13f4f794652ee5308590202731274b09627090ca6d0d53a868cc6f9eb5ed` |
| `docs/growth/organic-growth-plan.md` | `0bd8c72908ae80a420a742e9abaee2998eea57446729348fb19014e723b877d5` |
| `infra/posthog/runtime-guard.env.example` | `c623b312756d9c08226bb58823775a4e9e6890459204f00ff04e5175e059c59c` |
| `infra/scripts/alert-analytics-degradation.sh` | `75fb9f2d397d0beec6f3a8520e4ed0777dd08508df52289749ab57442eb9d865` |
| `infra/scripts/posthog-capacity.py` | `0ce0196939ee51cd0b4915fe977ff8aec7816482694f13a29d3bcde1741d7f0e` |
| `infra/scripts/posthog-runtime-guard.sh` | `0aacd8c4835ec5b6f4bcc9a1558076da384afdd2adf26f13fd9a91a7cfae6898` |
| `infra/scripts/posthog-storage.py` | `1dc62e52415778a3f6c18a1e0c926446eb4cbf8cc5ca6785ed6de3e7b9d26bba` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `d7a55b9b0c7ef99b8e4db5fa28136fd6c3748ccb376a94ec3f254712931e239b` |
| `specs/273-paid-traffic-analytics/plan.md` | `2b25a48d91640321fb47582b0d5fe2d0a249dfe72a8436a4a8c87b0188e9ffab` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4e885f846adf9890d04668df585b4485f8b23aa1eec70fbc0326f79ee0e52c4d` |
| `specs/273-paid-traffic-analytics/tasks.md` | `edbec930f15d85ff9b45a84d8d7ca6fe3b8133c69375cdb2849c3a7e9e75f2db` |
| `specs/273-paid-traffic-analytics/validation/t113-local-resource-20261030.md` | `19ec00e88a13306bceaa732d313cdab17827d414466c0dd01d2e259cda19d25c` |
| `specs/273-paid-traffic-analytics/validation/t113-local-resource-design-review-20261030.md` | `d37322184f66d5efb73db7762364d66dde0d3eee7aca6aac6ed8370ae295886f` |
