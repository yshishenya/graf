# F273/T113: независимый проектный гейт guard.service/timer

Дата: 30.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`47064a603994bffc889643f1794f44aa51ef2b05`, T113/#7804.
Путь проверки: `high-risk-product`, существующий Spec Kit. До кода.

## Решение

**SCOPED DESIGN / ANALYZE PASS: CRITICAL 0, HIGH 0; открытых P1: 0, P2: 0.**
Все117 вопросов перечитаны: **117 checked / 0 unchecked**, отметки не менялись.
Можно реализовать именно проверку двух существующих guard units и добавить
`AccuracySec=1s` в существующий timer. Полные installed jobs/cron/retention,
работающий local_only, ready/T0 и завершение T113 этим не принимаются.

Полностью прочитан конечный precode
`.dev/growth/t113-guard-units-precode-20261030.md`, SHA-256
`8b65a6d28fd1144bfd89fcba34a70443b987014444977d5c0ff2893af76bbefc`.
Он заменяет исходную версию
`1e21a6da424e0dfaf5cbefd0d82f50321a46c94ee7e5c62c2fa2a68cb0dcd754`:
до реализации в него внесены оба уточнения reviewer о ExecStartEx и адресе шины.
Полный ранее принятый алгоритм
[t113-full-operator-design-20261030.md](t113-full-operator-design-20261030.md)
не менялся: SHA-256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

## Текущий пробел и проверенные зависимости

Прочитаны полные source guard.service/timer, действующие `_runtime_operations`,
`_runtime_preflight`, `_command`, `_settings_file_identity`, `_settings_no_acl`,
`_settings_source_ancestors`, `_object`, guard freshness reader, затронутый
contract test и раздел runbook «Automated Runtime Guard».

Сейчас source timer содержит OnBootSec=2min, OnUnitActiveSec=1min,
Persistent=true и фиксированный service, но не AccuracySec. Действующий
runtime проверяет root-owned guard script и свежие состояния, но не source
и загруженные свойства timer/service. Следовательно, соответствие script
не является доказательством соответствия действительного расписания/ExecStart.
План закрывает этот конкретный пробел без выдачи полной готовности.

Прежний `_command` владеет CLI child до reap, ограничивает общим deadline и
сохраняет владение при повторной отмене. `_object` отвергает duplicate keys.
Источник полного алгоритма явно сохраняет доверие проверенному коду и root
установки; параллельные ручные root изменения в обход оператора не входят
в обещанную гарантию. Reader не становится новым sandbox для root.

## Минимальный алгоритм, принимаемый до кода

1. Только два фиксированных installed пути в `/etc/systemd/system`.
   Удержанные no-follow/nonblocking read-only FD, root:root0644, regular,
   single-link,0<size≤65536, без ACL. Ancestors без links, root-owned и без
   записи group/other. Сравнение actual bytes с доверенным snapshot и повторная
   проверка FD/path/ancestors/bytes после await и при выходе. Никаких установок.
2. Только native `/usr/bin/busctl` get-property для systemd1 и фиксированных
   object paths. Ограниченный ответ65536bytes, точные type/data, строгие
   вложенные типы/значения и отказ на неизвестной форме. Не выполнять shell,
   reload/start/enable; не читать environments приватных служб и не принимать
   supplied PASS. Непустой DBUS_SYSTEM_BUS_ADDRESS запрещён до/после property
   await, argv не содержит адресной/удалённой подмены; общий `_command` не меняется.
3. Проверять source identity и critical effective state отдельно: canonical
   Id/Names/FragmentPath, loaded/non-transient/no reload/no dropins/no SourcePath,
   timer enabled и active waiting/running, service static и только допустимую
   inactive/dead либо activating/start пару. Не выводить успех из одного
   NeedDaemonReload=false или равенства исходного файла.
4. Timer требует ровно два monotonic интервала120000000/60000000µs,
   пустой calendar, AccuracyUSec1000000, нулевую случайную задержку и прочие
   перечисленные precode boolean параметры. Абсолютный next_elapse должен
   иметь правильный неотрицательный целый тип, но исключается из digest.
5. Service требует прежние oneshot/root/argv/env-file/write-path/sandbox
   ограничения precode и пустые дополнительные команды/окружения/mounts.
   Помимо ExecStart обязателен **ExecStartEx**: точный type=a(sasasttttuii),
   ровно одна запись, прежние path/argv, **flags=[] именно list**. Legacy
   ignore-failure=false не доказывает отсутствия других префиксов исполнения.
   Семь динамических полей обеих форм — int, не bool; они не экспортируются
   и не участвуют в стабильном config digest.
6. Effective свойства перечитываются после yield. Digest нормализованной
   конфигурации должен совпасть. Допустимые пары состояния проверяются вновь,
   но tick, history/PID/timestamps и нормальное start→inactive не считаются
   изменением конфигурации. Порядок ReadWritePaths незначим, множество точное.
7. Контекст удерживается вокруг runtime DB и последующих await/проверок.
   Успешный возврат только после успешных exit checks всех контекстов.
   runtime_sha256 включает guard_units_sha256, публичный результат не получает
   raw units/argv/env/history. Прежние access/config digests не переопределяются.

AccuracySec=1s устраняет предусмотренное systemd минутное объединение пробуждений.
Это не гарантия исполнения в реальном времени. Предел0≤age<120с в
`runtime_guard_blockers` остаётся без изменений: задержка под нагрузкой,
неизвестный sample или incident latch продолжают блокировать допуск.

## Проверенные формы данных и границы наблюдения

Полностью прочитан metadata-only файл
`.dev/growth/t113-guard-units-native-format-20261030.json`, SHA-256
`f8d5e4c56b4961b40f6a6ec9f15a45d1a8640d2f4747f46009395aa62fa0f967`.
Он фиксирует безопасные read-only наблюдения исполнителя на astraglobal,
systemd259.5: direct type/data, TimersMonotonic a(stt), TimersCalendar a(sst),
ExecStartEx a(sasasttttuii) с flags list, PrivateTmp b, ProtectHome/ProtectSystem s,
BindPaths/BindReadOnlyPaths a(ssbt), TemporaryFileSystem a(ss).
Default AccuracyUSec60000000 подтверждает необходимость явного значения1с.

Это подтверждение формата на дистрибутивных units, **не installed proof GRAF**.
Reviewer не подключался к серверу. Прежнее наблюдение source/loaded ExecStart
расхождения на2brain.dev рассматривается как сообщённый исполнителем контекст;
текущая рабочая конфигурация этим ревью не установлена. Недоступность SSH и
неподтверждённое доверие installation UID не обходятся.

## Scoped analyze и обязательная проверка реализации

Использован ранее прочитанный `speckit-analyze`; current prerequisites
с `--json --require-tasks --include-tasks` подтвердили F273.
Before/after_analyze commit hooks явно disabled, изменяющие hooks не запускались.
Проведён ограниченный анализ связи принятого алгоритма с существующими задачами.

| Требование | Задача | Ограниченное покрытие |
| --- | --- | --- |
| FR-031/032 | T113, зависимость T116 | Текущий guard/freshness/latch сохраняются, расписание и критические effective параметры подтверждаются отдельно. |
| FR-036 | T113, зависимости T109–T111/T116 | Проверяется только guard unit часть installed-job binding; полный age-job/cron/retention proof остаётся открытым. |
| FR-038 | T113 | Сравниваются исходные bytes и критические фактически загруженные свойства; source equality не выдаётся за effective proof. |

Прямо затронутых FR4, покрыто4/4 существующей задачей; непокрытых новых задач0.
Новых категорий/получателей/прав/продуктовых решений нет. Противоречий
конституции, обязательных уточнений и дублирующих задач в конечном проекте нет.
Два обнаруженных пробела — Ex flags и bus override — устранены в конечном
precode до кода. Полный новый analyze всей фичи не заявляется.

Следующее code review должно потребовать causal RED до source изменения и
конечные проверки: file link/ACL/owner/mode/ancestry/bytes/смена пути; type/value,
duplicate JSON keys, extra commands/dropins/calendar/delay/disabled/stopped,
ExecStartEx flags и DBUS_SYSTEM_BUS_ADDRESS. Нужны положительные tick и
start→inactive, независимый отказ на exit drift, удержание guard контекста
вокруг DB и digest в результате. Отмена должна прерывать именно ожидание
property, не возвращать успех и сохранять прежнее владение child.

Actual root filesystem cases выполняются исполнителем на существующем Linux
образе/одноразовом volume без сети/socket/приложения; Mac skip их не заменяет.
Native systemd-analyze verify допустим только на временных source units,
без установки/загрузки/запуска. Полные contract модули alert+retention,
unit operator, Ruff/governance/process/fragments/links/whitespace остаются
обязательными. Эти будущие проверки ещё не объявляются пройденными.

## Контрольные списки и повторное чтение

Все117 вопросов перечитаны в этом проектном ревью; отметки прежние и относятся
к качеству требований. Для этого шага непосредственно важны privacy CHK031/032,
security CHK022/023 и infra CHK013/014/016–020/025: разные области деградации,
текущая конфигурация, сроки и независимый путь оповещения не подменяются
состоянием одного timer. Остальные вопросы не получают нового содержания.

| Список | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements |16|0|`6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2`|
| privacy-measurement |45|0|`8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f`|
| security |27|0|`57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8`|
| infra |29|0|`998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94`|
| Итого |117|0|Отметки не менялись.|

Применимые sections spec/operations/full operator design, текущие T113
дополнения plan/tasks, source units/helpers и runbook прочитаны непосредственно.
Хеши неизменных constitution/PRD/status/product-gates/spec/operations/data-model
и ранее принятых plan/tasks/quickstart совпадают с прошлым этапом.
Применено разрешённое исключение F273 на повторное чтение большого baseline;
повторное полное чтение600КБ истории не имитируется.

## Остаток и границы

`full_preflight_not_implemented` и `activation_recovery_unverified` сохраняются.
Полные host jobs/cron/purge/retention, shell graf-local, верхние
initial/backup/verify/actual-restore/resume, CD/rollback/daily, рабочие T0/ready,
аналитика/IP/получатели, exact-SHA CI/Full/release, T112/T113/#7804 и коммерческие
AC01–AC06 остаются открытыми. Результат не доказывает трафик или продажи.

Отдельный последующий остаток local_only не скрывается: действующий guard при
отсутствии PostHog containers создаёт `posthog_containers_missing` и disable
reason. Это подтверждено чтением script; текущий шаг его не меняет и не
объявляет local_only готовым. Принятие guard units не снимает этот HOLD.

Reviewer не запускал SSH/DB/Docker/tests/Dev/production, не менял source/spec/
plan/tasks/Git/GitHub/checklist marks. Изменён только этот отчёт.
После записи отчёт перечитан целиком;117/0 пересчитано.
