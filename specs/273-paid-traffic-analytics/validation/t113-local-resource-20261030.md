# F273/T113: локальный ресурсный путь

30.10.2026, ветка `codex/f273-local-period-20261029`, основа
`dc8b0cd055bccbc73cf5dbdf6302f88225c4f8bc`, T113/#7804.
Путь high-risk-product, существующий Spec Kit; Legacy Impact untouched.
[Проектное ревью](t113-local-resource-design-review-20261030.md):
SCOPED DESIGN/ANALYZE PASS,117/0, открытых P1/P2=0 до кода.
Конечный precode SHA256
`33a72287327881b59b6a8b2bd11c1546d112442aaa8eaac29906b9484728e369`.

## Изменение

Существующие collector/capacity/guard/alert и runtime consumers используют
явные posthog/graf-local. Default posthog сохраняет обязательные хранилища
и provider probes; local допускает доказанное отсутствие контейнеров, но
проверяет оба списка volumes, полные уникальные64hex Id и точное равенство
inspect, project/service labels и Name/mountpoint томов. Остаточные данные
всегда входят в учёт; неизвестное/частичное обнаружение закрывает готовность.
GRAF relations измеряются прежним metadata-only способом, без чтения строк.

Локальный путь не вызывает PostHog health/ClickHouse/queue probes даже после24ч;
provider-only показатели not_applicable. Product/host sensors, capacity,
budget/reserve и durable incident сохраняются. Выделенные архивы считаются
целиком; отсутствующие local archives допустимы только при безопасном
существующем родителе и ENOENT. Полные смешанные GRAF backups не приписываются
целиком аналитике: её доля неизвестна, точный90дневный прогноз этой доли не
заявляется. Защита actual FS обязательна. Поддержан fixed parent
/opt/projects/2brain-rec/backups, override только canonical прямой child на
том же FS без links. Guard не создаёт parent. Actual runtime проверяет этот
путь до/после работы, coherent backup helper отвергает иной parent.

Sample/alert version3 и protection/restore-receipt version2 привязаны к scope.
Scope включён в inventory digest; старые anchors/budgets не принимаются
автоматически. Старый/чужой incident остаётся HOLD без перезаписи; lstat
различает отсутствие и link. Manual restoration сохраняет прежние общие
proofs/readback и требует provider proofs для posthog либо
local_measurement_review для graf-local. Смена scope не заменяет proofs.
Provider readiness явно требует posthog, actual local_only operator — graf-local.
Сроки/128GiB/20%/10% не изменены. Новых служб/зависимостей/БД/endpoint нет.

## Проверки

Причинный RED до source:4FAIL на отсутствующих scope arguments. Журнал
`.dev/growth/t113-local-resource-red-20261030.log`.
Первая полная проверка:224PASS/2FAIL — прежняя synthetic fixture использовала
короткий фиктивный ID и не доходила до своего low-space сценария. Fixture
исправлена на полный ID и project label; все5 прежних low-space cases PASS.
Первый Ruff сообщил13 форматных ошибок новых тестов; исправлены, конечный PASS.

Первый полный набор двух contracts и unit operator:550PASS/104LinuxSKIP.
После добавления scope-матрицы retry/dryrun/autooff/parallel и строгой lexical
проверки backup override запущен окончательный повтор на конечных байтах;
результат **557PASS/104LinuxSKIP** в188.15с, два contracts целиком и unit
operator на конечных байтах. Журнал
`.dev/growth/t113-local-resource-frozen-20261030.log`. Отдельно readiness
consumers21PASS. Конечный Linux resource profile повторён:41PASS/0SKIP.
Изолированный Linux actual files/settings/runtime:175PASS/0SKIP, включая8
новых backup/scope cases. Linux resource profile41PASS/0SKIP: реальная POSIX
файловая система, synthetic Docker metadata/FS sensor boundaries, сеть none,
read-only source/deps, без Docker socket, --rm и временные зависимости.
Профили пересекаются и не суммируются. Linux pytest без asyncio plugin
выдаёт один config warning, но async tests в этом профиле не выбираются.
Mac сохраняет два прежних warnings pytest/Starlette.

Проверены local absence/residual data, short/duplicate/partial/extra Id,
wrong labels/Name, command errors/links/PermissionError, known disk19.9/9.9,
old/wrong scope, latched incident/once/retry/applyfail/dryrun/autooff,
manual restore proofs и сохранность исходного scope. Полный subprocess flow
использует actual collector→capacity→guard→state→runtime consumer; только
Docker metadata и FS sensor synthetic, product rows/socket/network отсутствуют.

Ruff, bash syntax, governance, development-process, fragment и whitespace
пройдены. SQL/миграции/сверка PG не менялись; предыдущие native PG proofs не
приписываются новым байтам. PG integration fixture лишь привязана к тому же
test-owned fixed parent. Полный native PG профиль этого среза не запускался.

## Scoped convergence и рабочий остаток

Конкретный проект покрыт прежними T113/T116; новые tasks/issues не требуются.
Нет новой совместимости старых форматов; legacy_new=0. Source-bound inventory
и independent code review обязательны до commit. Общие
full_preflight_not_implemented/activation_recovery_unverified остаются.
Installed jobs/cron/overrides, PostgreSQL staging FS/tmpfs+memory binding,
upper initial/backup/verify/restore/resume и предпусковой бюджет двух полных
копий/restore/staging ещё не приняты. Working protection v1 требует отдельного
trusted перехода с сохранением истории; автоматической миграции нет.
T112/T113/#7804, рабочий ready/T0, выпуск и AC01–AC06 открыты.

Read-only наблюдение 2brain.dev30.10 (SSH exit0): общий диск
1880373706752 байта, доступно337415598080 (17.94407126989791%). Ниже20%; до
ровно20% не хватает38659143270.4 байта. Ничего не очищалось. sudo-n недоступен,
текущий guard state непривилегированно не читается. Installed units отличаются
от нового source, timer AccuracyUSec60000000 вместо1000000. Это не проверка
полной installed готовности и не доказательство ошибки/зависания службы.
Docker сообщает Images211.7GB/reclaimable91.61GB, Build Cache65.51GB/
reclaimable18.74GB; reclaimable не доказывает безопасность удаления pinned
release/rollback образов и активных проверок. Prune/volumes/данные/история/
архивы не изменялись. SSH доступен: прежний connection-refused blocker устарел.

Аналитика/IP/внешние получатели не включены. Новый трафик, активации и продажи
этим этапом не доказаны; T0 ещё не назначен. Product Radar после выпуска и
достоверного измерения по решению владельца. Другая release-задача не дала
подтверждённого freeze; бессрочное окно не запрашивалось.
